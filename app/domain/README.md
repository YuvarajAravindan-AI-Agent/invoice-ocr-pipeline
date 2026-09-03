# domain

Business rules only. No cloud SDK imports, no provider-specific types,
no environment variables read directly here. If this layer needs
something from the outside world (storage, secrets, events, scheduling),
it depends on a port interface defined in `../application/`, never on a
concrete adapter.
