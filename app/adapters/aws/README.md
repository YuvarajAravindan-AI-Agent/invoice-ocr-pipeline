# adapters/aws

Concrete implementations of the ports defined in `../../application/`,
using the aws SDK. This is the only place aws-specific
client code should appear in the application layer — the domain layer
must never import it directly.
