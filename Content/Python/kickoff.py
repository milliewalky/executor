from typing import Optional, Callable
from host_executor import HostExecutor

import unreal

# NOTE(mmacieje): In an embedded environment like Unreal Engine’s Python
# support, the interpreter is long-running. This means that global variables
# are stored in the module’s namespace. Since the module isn’t reloaded or
# discarded between uses in a persistent interpreter, its global state (i.e.,
# the values of its global variables) remains unchanged unless modified by your
# code

tick: Optional[object] = None
executor: Optional[unreal.MoviePipelineExecutorBase] = None

def on_movie_pipeline_executor_errored(executor: unreal.MoviePipelineExecutorBase, pipeline: unreal.MoviePipeline, fatal: bool, msg: unreal.Text):
    base_str: str = f"`{executor}` executor -> `{pipeline}` pipeline -> '{msg}'"

    maybe_fatal_str: str = ""
    log_callable: Callable[Any]
    if fatal:
        maybe_fatal_str = "the execution is fatally wounded."
        log_callable = unreal.log_error
    else:
        maybe_fatal_str = "this is fine, though."
        log_callable = unreal.log_warning

    log_callable(f"{base_str}; {maybe_fatal_str}")


def on_executor_finished(_executor: unreal.MoviePipelineExecutorBase, _success: bool):
    # NOTE(mmacieje): This `success` boolean is unreliable—errors are flagged
    # as successful. For accurate status, retrieve information from the
    # individual job work callbacks on the PIE Executor and propagate it via a
    # custom delegate if necessary.

    unreal.SystemLibrary.quit_editor()


def wait_for_asset_registry(_delta: float):
    if unreal.AssetRegistryHelpers.get_asset_registry().is_loading_assets() == False:
        global tick

        # mmacieje: (a) Unregister _the_ callback
        unreal.unregister_slate_pre_tick_callback(tick)

        global executor

        # mmacieje: Instantiate _the_ Executor
        #
        # This dummy executor is designed to host an executor implemented in
        # Python. Python-defined `UClass`es are not available when the executor
        # is initialised, and not all callbacks are accessible from Python. By
        # subclassing this class in Python and specifying the `UClass` to spawn
        # latently, certain events can be forwarded to Python by overriding the
        # appropriate functions.
        #
        # Fair choice.
        executor = HostExecutor()

        # mmacieje: Set up its properties.
        executor.target_pipeline_class = unreal.MoviePipeline
        executor.user_data = "If you truly wished, you could paste a JSON file here"

        # mmacieje: Set up its callbacks. Here, we configure all callbacks so that the sample
        # is exhaustive, although some implementations are dummy.
        executor.on_executor_errored_delegate.add_callable_unique(on_movie_pipeline_executor_errored)
        executor.on_executor_finished_delegate.add_callable_unique(on_executor_finished)

        # mmacieje: (b) Kick off the jobs
        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        subsystem.render_queue_with_executor_instance(executor)
    else:
        unreal.log_warning("Asset Registry subsystem is still indexing assets...")


def entry_point():
    # mmacieje: Asset Registry may still be loading assets by the time this is
    # called. Therefore, we should wait until it has finished indexing (or parsing?)
    # all assets in the project before proceeding, as any attempts to look up the
    # assets may fail unexpectedly. This registers a per‐tick callback that is
    # invoked once per frame. Once Asset Registry reports that it is fully loaded,
    # we will (a) unregister this callback and (b) initiate Movie Pipeline jobs.
    # This ensures that rendering is started only once.
    global tick
    tick = unreal.register_slate_pre_tick_callback(wait_for_asset_registry)


if __name__ == "__main__":
    entry_point()
