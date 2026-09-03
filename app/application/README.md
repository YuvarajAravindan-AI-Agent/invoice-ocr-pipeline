# application

Use cases and **ports** — the interfaces the domain layer depends on,
e.g. `ObjectStore.put()`, `SecretProvider.get()`, `EventBus.publish()`,
`JobScheduler.schedule()`. Each port gets one implementation per
provider under `../adapters/<provider>/`. Define the port here even
before a second adapter exists — that's what keeps the first
implementation from silently becoming the only one that's possible.
