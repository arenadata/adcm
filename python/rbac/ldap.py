# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from contextlib import contextmanager, suppress
import os
import re

from cm.adcm_config.ansible import ansible_decrypt
from cm.errors import raise_adcm_ex
from cm.logger import logger
from cm.models import ADCM, ConfigLog
from django.contrib.auth.models import Group as DjangoGroup
from django.db.transaction import atomic
from django_auth_ldap.backend import LDAPBackend, _LDAPUser
from django_auth_ldap.config import LDAPSearch, MemberDNGroupType
import ldap

from rbac.models import Group, OriginType, User

CERT_ENV_KEY = "LDAPTLS_CACERT"
CN_PATTERN = re.compile(r"CN=(?P<common_name>.*?)[,$]", re.IGNORECASE)
ENCODING = "utf-8"
USER_PLACEHOLDER = "%(user)s"


def _process_extra_filter(filterstr: str) -> str:
    filterstr = filterstr or ""
    if filterstr == "":
        return filterstr

    # simple single filter ex: `primaryGroupID=513`
    if "(" not in filterstr and ")" not in filterstr:
        return f"({filterstr})"
    # assume that composed filter is syntactically valid
    return filterstr


def configure_tls(
    enabled: bool,
    cert_filepath: str = "",
    conn: ldap.ldapobject.LDAPObject | None = None,
) -> dict | None:
    os.environ.pop(CERT_ENV_KEY, None)
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    if not enabled:
        return None

    if cert_filepath:
        os.environ[CERT_ENV_KEY] = cert_filepath

    opts = {
        ldap.OPT_X_TLS_CACERTFILE: cert_filepath,
        ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_ALLOW,
        ldap.OPT_X_TLS_NEWCTX: 0,
    }

    if not conn:
        return opts

    for opt_key, opt_val in opts.items():
        conn.set_option(opt_key, opt_val)
    return None


def is_tls(ldap_uri: str) -> bool:
    if "ldaps://" in ldap_uri.lower():
        return True
    return False


def get_ldap_config() -> dict | None:
    adcm_object = ADCM.objects.first()
    if not adcm_object:
        return None

    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if current_configlog.attr["ldap_integration"]["active"]:
        return current_configlog.config["ldap_integration"]

    return None


def get_groups_by_user_dn(
    user_dn: str,
    user_search: LDAPSearch,
    conn: ldap.ldapobject.LDAPObject,
) -> tuple[list[str], list[str], str | None]:
    err_msg = None
    user_name_attr = get_ldap_config()["user_name_attribute"]
    replace = f"{user_name_attr}={USER_PLACEHOLDER}"
    search_expr = f"distinguishedName={user_dn}"

    users = conn.search_s(
        base=user_search.base_dn,
        scope=user_search.scope,
        filterstr=user_search.filterstr.replace(replace, search_expr),
    )
    if len(users) != 1:
        err_msg = f"Not one user found by `{search_expr}` search"
        return [], [], err_msg

    user_dn_, user_attrs = users[0]
    if user_dn_.strip().lower() != user_dn.strip().lower():
        err_msg = f"Got different user dn: {(user_dn_, user_dn)}. Tune search"
        return [], [], err_msg

    group_cns = []
    group_dns_lower = []
    for group_dn in user_attrs.get("memberOf", []):
        # v3 protocol uses utf-8 encoding
        # https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-2000-server/cc961766(v=technet.10)?redirectedfrom=MSDN#differences-between-ldapv2-and-ldapv3
        group_dns_lower.append(group_dn.decode("utf-8").lower())
        group_name = " ".join(CN_PATTERN.findall(group_dn.decode(ENCODING)))
        if group_name:
            group_cns.append(group_name)

    logger.debug("Found %s groups by user dn `%s`: %s", len(group_cns), user_dn, group_cns)
    return group_cns, group_dns_lower, err_msg


def get_user_search(ldap_config: dict) -> LDAPSearch:
    return LDAPSearch(
        base_dn=ldap_config["user_search_base"],
        scope=ldap.SCOPE_SUBTREE,
        filterstr=f"(&"
        f"(objectClass={ldap_config.get('user_object_class') or '*'})"
        f"({ldap_config['user_name_attribute']}={USER_PLACEHOLDER})"
        f"{_process_extra_filter(ldap_config.get('user_search_filter'))}"
        f")",
    )


def get_ldap_default_settings() -> tuple[dict, str | None]:
    ldap_config = get_ldap_config()
    if ldap_config:
        configure_tls(enabled=False)
        group_search = None
        if ldap_config["group_search_base"]:
            group_search = LDAPSearch(
                base_dn=ldap_config["group_search_base"],
                scope=ldap.SCOPE_SUBTREE,
                filterstr=f"(&(objectClass={ldap_config.get('group_object_class') or '*'})"
                f"{_process_extra_filter(ldap_config.get('group_search_filter'))})",
            )
        user_attr_map = {
            "username": ldap_config["user_name_attribute"],
            "first_name": "givenName",
            "last_name": "sn",
            "email": "mail",
        }
        group_type = MemberDNGroupType(
            member_attr=ldap_config["group_member_attribute_name"],
            name_attr=ldap_config["group_name_attribute"],
        )

        default_settings = {
            "SERVER_URI": ldap_config["ldap_uri"],
            "BIND_DN": ldap_config["ldap_user"],
            "BIND_PASSWORD": ansible_decrypt(ldap_config["ldap_password"]),
            "USER_SEARCH": get_user_search(ldap_config),
            "USER_OBJECT_CLASS": ldap_config.get("user_object_class", "*"),
            "USER_FILTER": _process_extra_filter(ldap_config.get("user_search_filter", "")),
            "GROUP_FILTER": _process_extra_filter(ldap_config.get("group_search_filter", "")),
            "USER_ATTR_MAP": user_attr_map,
            "ALWAYS_UPDATE_USER": True,
            "CACHE_TIMEOUT": 0,
            "GROUP_DN_ADCM_ADMIN": [group_dn.lower() for group_dn in ldap_config["group_dn_adcm_admin"] or []],
        }
        if group_search:
            default_settings.update(
                {
                    "GROUP_SEARCH": group_search,
                    "GROUP_TYPE": group_type,
                    "GROUP_OBJECT_CLASS": ldap_config.get("group_object_class", "*"),
                    "MIRROR_GROUPS": True,
                    "FIND_GROUP_PERMS": True,
                },
            )

        if is_tls(ldap_config["ldap_uri"]):
            cert_filepath = ldap_config.get("tls_ca_cert_file", "")
            if not cert_filepath or not os.path.exists(cert_filepath):  # noqa: PTH110
                msg = "NO_CERT_FILE"
                logger.warning(msg)
                return {}, msg
            connection_options = configure_tls(enabled=True, cert_filepath=cert_filepath)
            default_settings.update({"CONNECTION_OPTIONS": connection_options})

        return default_settings, None

    return {}, "NO_LDAP_SETTINGS"


class CustomLDAPBackend(LDAPBackend):
    def __init__(self):
        self.default_settings = {}
        self.is_tls = False

    def authenticate_ldap_user(self, ldap_user: User | _LDAPUser, password: str) -> _LDAPUser | None:
        self.default_settings, _ = get_ldap_default_settings()
        if not self.default_settings:
            return None
        self.is_tls = is_tls(self.default_settings["SERVER_URI"])

        try:
            if not self._check_user(ldap_user):
                return None
            user_local_groups = self._get_local_groups_by_username(ldap_user._username)
            user_or_none = super().authenticate_ldap_user(ldap_user, password)
        except Exception as e:  # noqa: BLE001
            logger.exception(e)
            return None

        if isinstance(user_or_none, User):
            user_or_none.type = OriginType.LDAP
            user_or_none.is_active = True
            is_in_admin_group = self._process_groups(user_or_none, ldap_user.dn, user_local_groups)
            if is_in_admin_group:
                user_or_none.is_superuser = True
            elif user_or_none.is_superuser:
                user_or_none.is_superuser = False
            user_or_none.save(update_fields=["type", "is_active", "is_superuser"])

        return user_or_none

    @property
    def _group_search_enabled(self) -> bool:
        return "GROUP_SEARCH" in self.default_settings and bool(self.default_settings.get("GROUP_SEARCH"))

    @staticmethod
    def _get_local_groups_by_username(username: str) -> list[Group]:
        with suppress(User.DoesNotExist):
            user = User.objects.get(username__iexact=username, type=OriginType.LDAP)
            return [g.group for g in user.groups.order_by("id") if g.group.type == OriginType.LOCAL]

        return []

    def get_user_model(self) -> type[User]:
        return User

    @contextmanager
    def _ldap_connection(self) -> ldap.ldapobject.LDAPObject:
        ldap.set_option(ldap.OPT_REFERRALS, 0)
        conn = ldap.initialize(self.default_settings["SERVER_URI"])
        conn.protocol_version = ldap.VERSION3
        configure_tls(self.is_tls, os.environ.get(CERT_ENV_KEY, ""), conn)
        conn.simple_bind_s(self.default_settings["BIND_DN"], self.default_settings["BIND_PASSWORD"])
        try:
            yield conn
        finally:
            conn.unbind_s()

    def _get_groups_by_group_search(self) -> list[tuple[str, dict]]:
        with self._ldap_connection() as conn:
            groups = self.default_settings["GROUP_SEARCH"].execute(conn)
        logger.debug("Found %s groups: %s", len(groups), [i[0] for i in groups])
        return groups

    def _process_groups(self, user: User | _LDAPUser, user_dn: str, additional_groups: list[Group] = ()) -> bool:
        is_in_admin_group = False
        with self._ldap_connection() as conn:
            ldap_group_names, ldap_group_dns, err_msg = get_groups_by_user_dn(
                user_dn=user_dn,
                user_search=self.default_settings["USER_SEARCH"],
                conn=conn,
            )
            if err_msg:
                raise_adcm_ex(code="GROUP_CONFLICT", msg=err_msg)

        if any(group_dn in self.default_settings["GROUP_DN_ADCM_ADMIN"] for group_dn in ldap_group_dns):
            is_in_admin_group = True

        if not self._group_search_enabled:
            logger.warning("Group search is disabled. Getting all user groups")
            for ldap_group_name in ldap_group_names:
                group, _ = Group.objects.get_or_create(name=f"{ldap_group_name} [ldap]", type=OriginType.LDAP)
                group.user_set.add(user)

            return is_in_admin_group

        ldap_groups = list(zip(user.ldap_user.group_names, user.ldap_user.group_dns))
        # ldap-backend managed auth_groups
        for group in user.groups.filter(name__in=[i[0] for i in ldap_groups]):
            ldap_group_dn = self._get_ldap_group_dn(group.name, ldap_groups)
            rbac_group = self._get_rbac_group(group, ldap_group_dn)
            group.user_set.remove(user)
            rbac_group.user_set.add(user)
            if group.user_set.count() == 0:
                group.delete()
        for group in additional_groups:
            group.user_set.add(user)

        return is_in_admin_group

    def _check_user(self, ldap_user: _LDAPUser) -> bool:
        user_dn = ldap_user.dn
        if user_dn is None:
            return False
        username = ldap_user._username

        if User.objects.filter(username__iexact=username, type=OriginType.LOCAL).exists():
            logger.exception("usernames collision: `%s`", username)
            return False

        if self._group_search_enabled:
            group_member_attr = self.default_settings["GROUP_TYPE"].member_attr
            for _, group_attrs in self._get_groups_by_group_search():
                if user_dn.lower() in [i.lower() for i in group_attrs.get(group_member_attr, [])]:
                    break
            else:
                return False

        return True

    @staticmethod
    def _get_ldap_group_dn(group_name: str, ldap_groups: list) -> str:
        with suppress(IndexError):
            return [i for i in ldap_groups if i[0] == group_name][0][1]

        return ""

    @staticmethod
    def _get_rbac_group(group: Group | DjangoGroup, ldap_group_dn: str) -> Group:
        """
        Get corresponding rbac_group for auth_group or create `ldap` type rbac_group if not exists
        """
        if isinstance(group, Group):
            return group
        elif isinstance(group, DjangoGroup):  # noqa: RET505
            try:
                # maybe we'll need more accurate filtering here
                return Group.objects.get(name=f"{group.name} [{OriginType.LDAP.value}]", type=OriginType.LDAP.value)
            except Group.DoesNotExist:
                with atomic():
                    return Group.objects.create(
                        name=group.name,
                        type=OriginType.LDAP,
                        description=ldap_group_dn,
                    )
        else:
            raise TypeError("wrong group type")
