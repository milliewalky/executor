"""
Kickoff module for starting the custom rendering job using Unreal's Movie Pipeline.

The module registers a tick callback that waits for the asset registry to finish loading.
Once assets are loaded, it creates an instance of the custom executor, sets up a finished callback,
and tells Unreal to start rendering using that executor.
"""

from typing import Any, Optional

import unreal
import superb_executor

tick: Optional[Any] = None
executor: Optional[unreal.MoviePipelineExecutorBase] = None


def on_custom_executor_finished(executor: unreal.MoviePipelineExecutorBase, success: bool) -> None:
    """
    Callback function invoked when the custom executor finishes its work.

    Args:
        executor (SuperbExecutor): The executor instance that finished execution.
        success (bool): Indicates whether the execution was successful; NOTE: Due to how errors are reported, this flag may not be fully reliable.
    """
    _ = executor
    _ = success

    print(f"DONE! Quitting editor now!")

    unreal.SystemLibrary.quit_editor()


def wait_for_asset_registry(delta: float) -> None:
    """
    Tick callback that waits for the asset registry to finish loading.

    Once loading is complete, it unregisters itself, initializes the render job by
    creating a custom executor instance, and instructs Unreal to render via the Movie Pipeline Queue.

    Args:
        delta (float): Time elapsed since the last tick.
    """
    _ = delta

    asset_registry: unreal.AssetRegistry = unreal.AssetRegistryHelpers.get_asset_registry()
    good: bool = asset_registry.is_loading_assets() == 0

    if good:
        # mmacieje: Handle returned by Unreal's callback registration.
        global tick
        global executor

        # mmacieje: Unregister the tick callback now that the assets are loaded.
        unreal.unregister_slate_pre_tick_callback(tick)

        # mmacieje: Create an instance of the custom executor.
        executor = superb_executor.SuperbExecutor()

        # mmacieje: Register the callback to be notified when the executor finishes.
        executor.on_executor_finished_delegate.add_callable_unique(on_custom_executor_finished)

        # mmacieje: Retrieve the movie pipeline queue subsystem and start rendering using the custom executor.
        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        subsystem.render_queue_with_executor_instance(executor)
    else:
        unreal.log_warning("Still loading...")


# mmacieje: Register the 'wait_for_asset_registry' callback to be invoked on every slate pre-tick.
tick = unreal.register_slate_pre_tick_callback(wait_for_asset_registry)
