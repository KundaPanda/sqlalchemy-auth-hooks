resource User {
    permissions = ["query"];
    roles = ["reporter"];

    "query" if "reporter";
}

actor AuthUser {}

has_role(_actor: AuthUser, "reporter", _resource: Resource);

allow(actor: AuthUser, action, resource)
    if has_permission(actor, action, resource);