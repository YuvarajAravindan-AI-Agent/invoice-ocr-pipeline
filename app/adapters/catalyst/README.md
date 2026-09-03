# adapters/catalyst

Concrete implementations of the ports defined in `../../application/`,
using the catalyst SDK. This is the only place catalyst-specific
client code should appear in the application layer — the domain layer
must never import it directly.
