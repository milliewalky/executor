# Executor—A custom Python Movie Pipeline Play-In-Editor Executor for Unreal Engine

This repository provides a Python plug-in for Unreal Engine that implements a custom executor for the Movie Pipeline. By utilising Unreal’s Python API, the plug-in allows you to configure and run rendering jobs using command-line parameters. It enables detailed control over render settings such as resolution, frame rate, deferred passes, post-process materials, and anti-aliasing—making it an ideal solution for automated and batch rendering workflows. This promotes a one-dispatch, one-job workflow. If you wish to render multiple Level Sequences using different maps, I recommend running this script sequentially or, where possible, in parallel.

**This plug-in is intended for users familiar with Unreal Engine’s Python scripting and the Movie Pipeline subsystem.**

## Repository tour

### Concept

The plug-in consists of three main modules:

- **`init_unreal.py`**
  This module is automatically imported at editor startup. It ensures that the custom executor is registered and available to Unreal Engine by simply importing the core functionality.

- **`kickoff.py`**
  This module registers a tick callback that waits for the asset registry to finish loading. Once assets are ready, it creates an instance of the custom executor, sets up a callback to detect when the rendering job finishes, and instructs Unreal’s Movie Pipeline Queue to begin rendering.

- **`host_executor.py`**
  This module implements a custom Executor class named `HostExecutor`—a subclass of `unreal.MoviePipelinePythonHostExecutor`. It parses command-line parameters to determine the workload type (user-provided Sequence, Configuration, or Queue) and then dynamically configures rendering job settings including output resolution, anti-aliasing, deferred passes, post-process materials, and more.

Internally, the executor uses dictionaries to map parameter names to Unreal classes and asset references. It also demonstrates how to set up complex rendering configurations on the fly using Unreal’s Movie Pipeline settings.

### Files

```
executor
├── Content
│   ├── Python
│   │   ├── init_unreal.py
│   │   ├── kickoff.py
│   │   └── host_executor.py
│   └── PostProcessInput2.uasset
├── Executor.uplugin
```

- **`Content/Python`**
  Contains the plug-in’s core Python modules.

- **`Content/PostProcessInput2.uasset`**
  Features sample post-process material that can be fed to Movie Pipeline Queue.

- **`Executor.uplugin`**
  The plug-in descriptor that informs Unreal Engine of the module’s presence and capabilities.

Surprisingly, I would suggest reading through the code in the alphabetical order in which the files are arranged.

## Example usage

You may wish to clone this repository directly to `path/to/unreal/engine/Engine/Plugins` as 'Executor' (using a capitalised letter for consistency with other Unreal Engine plug-ins). Alternatively, download the repository, unpack it, rename the folder so that its initial letter is capitalised, and then move the folder into `path/to/unreal/engine/Engine/Plugins`—just ensure that the plug-in’s contents reside in the root directory of the 'Executor' folder. Finally, enable the plug-in in your project's Project Settings.

To launch a rendering job using this plug-in, start the Unreal Editor in command-line mode with the appropriate parameters. For example:

```console
path/to/unreal/engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe /Game/Optional/Path/To/Map/Map.Map path/to/project/Project.uproject -ExecCmds="py kickoff.py" -Sequence=/Game/Path/To/Level/Sequence/Sequence.Sequence -DeferredPass=Base -Width=2560 -Height=1440 -FrameRate=30 -Materials="PostProcessInput2" -SpatialSampleCount=2 -TemporalSampleCount=32 -StartFrame=0 -EndFrame=10
```

In this example:

- **`-ExecCmds="py kickoff.py"`**  
  Executes the `kickoff.py` module on startup, triggering the rendering job setup.
  
- **`-Sequence`**  
  Specifies the level sequence asset to be rendered.
  
- **`-DeferredPass`**  
  Selects the deferred pass type (e.g., Base, Unlit, DetailLighting, etc.).
  
- **`-Materials`**  
  Provides a comma-separated list of post-process material names.
  
- Other parameters (such as **`Width`**, **`Height`**, **`FrameRate`**, **`SpatialSampleCount`**, **`TemporalSampleCount`**, **`StartFrame`**, and **`EndFrame`**) configure the output resolution, frame range, and anti-aliasing settings.

## Command-line parameters & configuration

The custom executor parses several command-line arguments to set up the rendering job:

- **Workload kind:**
  - `Queue`
  - `Configuration`
  - `Sequence`

- **Output settings:**
  - `Width`, `Height` – Output resolution.
  - `FrameRate` – Frame rate for the render.
  - `StartFrame`, `EndFrame` – Custom frame range (if specified).

- **Anti-aliasing settings:**
  - `TemporalSampleCount`, `SpatialSampleCount` – Configure the number of samples for anti-aliasing.
  - `EngineWarmUpCount`, `RenderWarmUpCount` – Warm-up frame counts.

- **Deferred pass & materials:**
  - `DeferredPass` – Selects the type of deferred pass.
  - `Materials` – A comma-separated list of post-process material names to apply.

These parameters are dynamically parsed at runtime, and the executor configures Unreal Engine’s Movie Pipeline settings accordingly.

## Further notes

For more information on Unreal Engine’s Movie Pipeline and Python integration, please refer to the [Unreal Engine Documentation](https://docs.unrealengine.com/).
