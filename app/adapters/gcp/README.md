# adapters/gcp

Concrete implementations of the ports defined in `../../application/`,
using the gcp SDK. This is the only place gcp-specific
client code should appear in the application layer — the domain layer
must never import it directly.
