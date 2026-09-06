# adapters/alibaba

Concrete implementations of the ports defined in `../../application/`,
using the alibaba SDK. This is the only place alibaba-specific
client code should appear in the application layer — the domain layer
must never import it directly.
