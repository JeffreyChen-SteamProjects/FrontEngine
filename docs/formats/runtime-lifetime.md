# Embedded runtime lifetime

FrontEngine retains ownership of its settings directory until its admitted work and
owned windows have retired. Atomic file replacement alone does not prevent an old
process from overwriting newer settings or home state.

## Main window

`FrontEngineMainUI` retains its four constructor arguments. Each process admits one
live or retiring main window. A second constructor raises `MainRuntimeInUse` before
reading settings. JEditor and PyBreeze reuse their embedded window, including when
moving it between a tab and a dock.

`request_shutdown()` returns `CloseDisposition`:

| Result | Host action |
| --- | --- |
| `REFUSED` | Keep the window and its state available for correction and retry. |
| `DRAINING` | Keep its container until `shutdown_finished` is emitted. |
| `CLOSED` | Remove the container. |

Connect the completion handler before requesting shutdown. Embedded FrontEngine
does not exit the host's `QApplication`. A deferred host-close attempt checks other
tools for unsaved changes again because the user may have edited them while waiting.

Preparation saves pet and home state, settings, notes, the last session and usage
history before destructive cleanup. A save refusal restores callback admission.
Already successful writes and canceled activities are not rolled back. Completion
deliveries queued during preparation resume after refusal; successful retirement
discards them.

## Individual settings pages

An embedding host opens `DefaultSettingsLifetime` before constructing a settings
page and supplies it as the required `lifetime=` keyword. The page captures that
lifetime. A delayed callback does not select whichever lifetime is currently active.

The host completes the page's domain-specific saves and shutdown before calling
`lifetime.close()`. Connect to `lifetime.finished` first and retain the lifetime until
completion. Closing the lifetime is not a substitute for saving a pet, shutting down
a home service or stopping a page's producers.

Multiple live default scopes share the same settings binding without reloading the
exported dictionary. Opening a default scope for a different current directory is
refused. After the last scope and its clients retire, a new scope can acquire the
directory and load the latest disk state.

Standalone pet widgets use an explicitly supplied `PetProfiles` adapter, or an
already open default settings lifetime when profiles are omitted. Synchronous pet
customization dialogs retain their explicit-profile contract; embedded callers also
supply the captured lifetime so Apply is rejected after shutdown admission ends.

`StorageSession.open(directory)` remains the explicit independent-directory API.
`HomeSaveStore` requires a `StorageSession`; raw paths are not accepted. One store
owns each home mode, and one service attaches to a store. A successfully constructed
service owns that store through shutdown. If service construction fails, the caller
still owns the store and must close it.

## Background work and callbacks

`WorkLifetime` supplies storage-free worker and callback ownership for standalone
media sources. `DefaultSettingsLifetime` adds the default settings binding. A
standalone source can own its work lifetime without acquiring settings storage.

Use the captured lifetime's `guard` or `connect_owned` for external callbacks,
`submit` for pooled jobs, `register_pending` for other work whose termination can be
observed, and `adopt` for owned top-level objects. Pools belong to the lifetime;
unrelated work in the host's global pool does not delay FrontEngine shutdown.
Comparison jobs retain a two-worker limit. Home art providers also keep a private
two-worker pool, registered with the supplied lifetime; closing the home does not
block the GUI thread while that pool drains.

Page actions and resource allocation use `owned_action` to reject new user work
outside LIVE, including during preparation. Completion methods use `owned_callback`
so a refused save can replay an admitted job's result. A rejected user action is
not replayed when preparation is canceled. Modal actions recheck the captured
lifetime after the dialog returns and before applying its result.

The UI adapters keep Qt's Python-slot argument adaptation: surplus positional
signal fields are discarded for fixed-arity Python handlers, while `*args` handlers
receive every field. The same adaptation applies when calling these UI adapters
directly. Defaults and keyword arguments still belong to the original handler;
missing required arguments and errors raised by the handler are not swallowed.
Native callables without an inspectable signature receive the supplied arguments.

Stopping a producer must retain any still-running handle so its completion can be
observed. A cleared UI busy flag is not worker completion. The lifetime disposes
owned objects after work ends and releases storage after their destruction.
Standalone hosts remain responsible for waiting before terminating their application.

## Cooperative API v1 plugins

Trusted plugin pages retain the API v1 QWidget factory contract. A page can implement
`bind_lifetime(lifetime)` to capture scoped facilities before starting asynchronous
work. Start that work after binding, register non-pool completion predicates and use
guarded result callbacks. Register overlay ownership as well as cleanup.

`shutdown()` is a cooperative promise that synchronous page work has stopped.
Registered asynchronous work must still drain. A shutdown exception or unfinished
registered work keeps retirement pending and storage owned. MainUI reports cleanup
failures through `shutdown_failed(error)` and its status bar; `lifetime.error` retains
the exception. Repeated close requests do not replay partly completed cleanup. Arbitrary unregistered
plugin threads are outside this completion guarantee.

## Persistence boundaries

Bound profile, command-history and palette adapters check their captured owner
before reading or changing state. Their read/modify/save/rollback operations share
a settings transaction. Retained adapters reject use after their owner closes.
Borrowed raw settings dictionaries do not provide synchronized mutation or protection
against arbitrary calls made outside the owning lifetime.

Settings, pet and palette exports validate the destination and temporary path.
Reserved settings, home, backup, temporary and lock filenames, and linked destination
files are rejected. This is a cooperative local-filesystem contract, not protection
against another process maliciously swapping paths after validation.

## GIF overlay resources

A GIF overlay owns its QMovie as a Qt child. Completing QObject deletion releases the decoder and source file even when Python references to the closed overlay or movie remain. Stopping playback alone does not release the source file.
