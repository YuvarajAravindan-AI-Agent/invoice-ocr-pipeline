# adapters/azure

Concrete implementations of the ports defined in `../../application/`,
using the azure SDK. This is the only place azure-specific
client code should appear in the application layer — the domain layer
must never import it directly.
