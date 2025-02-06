"""
Custom Movie Pipeline Executor for Unreal Engine.

This module implements a custom executor (SuperbExecutor) that configures and runs rendering jobs
via Unreal’s Movie Pipeline. It interprets command-line arguments to set up job parameters,
builds the rendering job (or queue), and then executes the jobs sequentially.
"""

from typing import Any, Dict, List
import unreal

# mmacieje: Global dictionaries mapping string keys to Unreal classes or asset references.
deferred_passes_name_type_dict: Dict[str, Any] = {
    "base": unreal.MoviePipelineDeferredPassBase,
    "unlit": unreal.MoviePipelineDeferredPass_Unlit,
    "detaillighting": unreal.MoviePipelineDeferredPass_DetailLighting,
    "lightingonly": unreal.MoviePipelineDeferredPass_LightingOnly,
    "reflectionsonly": unreal.MoviePipelineDeferredPass_ReflectionsOnly,
    "pathtracer": unreal.MoviePipelineDeferredPass_PathTracer,
    "objectid": unreal.MoviePipelineObjectIdRenderPass,
}

materials_name_ref_dict: Dict[str, str] = {
    "postprocessinput2": "/Executor/PostProcessInput2.PostProcessInput2",
}

console_vars_name_value_dict: Dict[str, int] = {
    # mmacieje: "your.Console.Variable": <its_value>,
    "r.Nanite": 0,
}

# mmacieje: Workload types
SEQUENCE: int = 0
CONFIGURATION: int = 1
QUEUE: int = 2


@unreal.uclass()
class SuperbExecutor(unreal.MoviePipelinePythonHostExecutor):
    """
    Custom executor for handling movie pipeline rendering jobs.

    It reads command-line parameters to decide whether to build a job from a sequence, configuration,
    or an entire queue. Then, it sets up the appropriate job configuration (output resolution,
    anti-aliasing, post-processing, etc.) and executes the job(s) in sequence.
    """
    # mmacieje: Unreal properties (the underlying types are defined by Unreal's API)
    job_idx = unreal.uproperty(int)
    queue = unreal.uproperty(unreal.MoviePipelineQueue)
    processing_queue = unreal.uproperty(unreal.MoviePipelineQueue)
    play_in_editor_executor = unreal.uproperty(unreal.MoviePipelinePIEExecutor)

    def _post_init(self) -> None:
        """
        Post-initialization: Set initial values for instance variables.
        """
        self.job_idx = -1
        self.queue = None
        self.processing_queue = None
        self.play_in_editor_executor = None

    @unreal.ufunction(override=True)
    def execute_delayed(self, queue: Any) -> None:
        """
        Called (after a short delay) to start the rendering job setup based on command-line parameters.

        Args:
            queue: A dummy parameter required by the interface (ignored).
        """
        _ = queue

        # mmacieje: Parse the command line into tokens, switches, and arguments.
        cmdln_tokens, cmdln_switches, cmdln_args = unreal.SystemLibrary.parse_command_line(
            unreal.SystemLibrary.get_command_line()
        )

        def find_needle(haysack: List[Any], needle: Any) -> bool:
            """
            Checks if a given value (needle) exists within a list (haysack).

            Args:
                haysack: A list of items to search.
                needle: The item to look for.

            Returns:
                True if the needle is found, False otherwise.
            """
            for item in haysack:
                if item == needle:
                    return True
            return False

        # mmacieje: Extract command-line arguments, converting to proper types and providing defaults.
        queue_ref: str = str(cmdln_args.get("Queue", ""))
        configuration_ref: str = str(cmdln_args.get("Configuration", ""))
        sequence_ref: str = str(cmdln_args.get("Sequence", ""))
        width: int = int(cmdln_args.get("Width", 1920))
        height: int = int(cmdln_args.get("Height", 1080))
        start_frame: int = int(cmdln_args.get("StartFrame", -1))
        end_frame: int = int(cmdln_args.get("EndFrame", -1))
        frame_rate: int = int(cmdln_args.get("FrameRate", 30))
        temporal_sample_count: int = int(cmdln_args.get("TemporalSampleCount", 1))
        spatial_sample_count: int = int(cmdln_args.get("SpatialSampleCount", 1))
        deferred_pass: str = str(cmdln_args.get("DeferredPass", "Base")).lower()
        materials: str = cmdln_args.get("Materials", "")
        multilayer: bool = find_needle(cmdln_switches, "Multilayer")
        engine_warm_up_count: int = int(cmdln_args.get("EngineWarmUpCount", 101))
        render_warm_up_count: int = int(cmdln_args.get("RenderWarmUpCount", 97))

        # mmacieje: Get the current map reference from the editor world.
        world_ref = unreal.EditorLevelLibrary.get_editor_world()
        package_ref = world_ref.get_outer()
        map_ref: str = package_ref.get_path_name()

        # mmacieje: Determine the type of workload based on which command-line arguments are provided.
        workload_kind: int = -1
        if sequence_ref:
            workload_kind = SEQUENCE
        if configuration_ref:
            workload_kind = CONFIGURATION
        if queue_ref:
            workload_kind = QUEUE

        workload_good: bool = False

        # mmacieje: Configure the rendering job based on the workload type.
        match workload_kind:
            # mmacieje: SEQUENCE
            case 0:
                # mmacieje: Create a new movie pipeline queue and allocate a job.
                self.queue = unreal.MoviePipelineQueue()
                job = self.queue.allocate_new_job()

                # mmacieje: Set metadata and asset references for the job.
                job.comment = u"Midas (/ˈmaɪdəs/; Ancient Greek: Μίδας) was a king of Phrygia with whom many myths became associated, as well as two later members of the Phrygian royal house."
                job.job_name = "Midas"
                job.map = unreal.SoftObjectPath(map_ref)
                job.sequence = unreal.SoftObjectPath(sequence_ref)

                configuration = job.get_configuration()

                # mmacieje: High-resolution rendering settings.
                high_resolution_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineHighResSetting)
                high_resolution_setting.allocate_history_per_tile = True
                high_resolution_setting.burley_sample_count = 64
                high_resolution_setting.overlap_ratio = 0
                high_resolution_setting.override_sub_surface_scattering = True
                high_resolution_setting.texture_sharpness_bias = 0
                high_resolution_setting.tile_count = 1

                # mmacieje: Output settings.
                output_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
                output_setting.use_custom_playback_range = (start_frame != -1 and end_frame != -1)
                output_setting.custom_end_frame = end_frame
                output_setting.custom_start_frame = start_frame
                output_setting.output_resolution = unreal.IntPoint(width, height)
                output_setting.use_custom_frame_rate = True
                output_setting.output_frame_rate = unreal.FrameRate(numerator=frame_rate)
                output_setting.zero_pad_frame_numbers = 4
                output_setting.output_directory = unreal.DirectoryPath(path=f"{{project_dir}}/Saved/MovieRenders/{{output_resolution}}_{{temporal_sample_count}}_{{spatial_sample_count}}_{frame_rate}_{deferred_pass}")
                output_setting.file_name_format = f"{{render_pass}}/{{frame_number}}"

                # mmacieje: Configure the deferred pass settings.
                deferred_pass_obj = configuration.find_or_add_setting_by_class(deferred_passes_name_type_dict[deferred_pass])
                material_name_list: List[str] = [item.strip() for item in materials.split(",") if item.strip()]
                material_ref_list: List[str] = []
                for material_name in material_name_list:
                    material_ref = materials_name_ref_dict.get(material_name.lower())
                    if material_ref:
                        material_ref_list.append(material_ref)

                # mmacieje: Debug output: print the material dictionaries and lists.
                print(materials_name_ref_dict)
                print(material_name_list)
                print(material_ref_list)

                # mmacieje: For each material reference, add a post process pass to the deferred pass.
                for material_ref in material_ref_list:
                    post_process_pass = unreal.MoviePipelinePostProcessPass()
                    post_process_pass.enabled = True
                    post_process_pass.material = unreal.load_asset(material_ref)
                    deferred_pass_obj.additional_post_process_materials.append(post_process_pass)

                deferred_pass_obj.disable_multisample_effects = True
                deferred_pass_obj.render_main_pass = True

                # mmacieje: Anti-aliasing settings.
                anti_aliasing_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
                anti_aliasing_setting.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE
                anti_aliasing_setting.engine_warm_up_count = engine_warm_up_count
                anti_aliasing_setting.override_anti_aliasing = True
                anti_aliasing_setting.render_warm_up_count = render_warm_up_count
                anti_aliasing_setting.render_warm_up_frames = True
                anti_aliasing_setting.spatial_sample_count = spatial_sample_count
                anti_aliasing_setting.temporal_sample_count = temporal_sample_count
                anti_aliasing_setting.use_camera_cut_for_warm_up = False

                # mmacieje: EXR image sequence output settings.
                exr_output_configuration = configuration.find_or_add_setting_by_class(
                    unreal.MoviePipelineImageSequenceOutput_EXR
                )
                exr_output_configuration.compression = unreal.EXRCompressionFormat.PIZ
                total_sample_count_threshold: int = 128
                if spatial_sample_count * temporal_sample_count == total_sample_count_threshold:
                    exr_output_configuration.compression = unreal.EXRCompressionFormat.ZIP
                exr_output_configuration.multilayer = multilayer

                # mmacieje: Console variable settings.
                console_variable_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
                for console_var, value in console_vars_name_value_dict.items():
                    console_variable_setting.add_or_update_console_variable(console_var, value)

                # mmacieje: Game override settings.
                game_override = configuration.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
                game_override.cinematic_quality_settings = True
                game_override.disable_hlo_ds = True
                game_override.flush_grass_streaming = False
                game_override.flush_streaming_managers = True
                game_override.game_mode_override
                game_override.override_view_distance_scale = True
                game_override.override_virtual_texture_feedback_factor = True
                game_override.shadow_distance_scale
                game_override.shadow_radius_threshold
                game_override.texture_streaming = unreal.MoviePipelineTextureStreamingMethod.FULLY_LOAD
                game_override.use_high_quality_shadows = True
                game_override.use_lod_zero = True
                game_override.view_distance_scale
                game_override.virtual_texture_feedback_factor

                # mmacieje: Initialize any transient (temporary) settings and assign the configuration.
                configuration.initialize_transient_settings()
                job.set_configuration(configuration)

                workload_good = True

            # mmacieje: CONFIGURATION
            case 1:
                # mmacieje: Create a new job and load a pre-existing configuration asset.
                self.queue = unreal.MoviePipelineQueue()
                job = self.queue.allocate_new_job()
                job.comment = u"Midas (/ˈmaɪdəs/; Ancient Greek: Μίδας) was a king of Phrygia with whom many myths became associated, as well as two later members of the Phrygian royal house."
                job.job_name = "Midas"
                job.map = unreal.SoftObjectPath(map_ref)
                job.sequence = unreal.SoftObjectPath(sequence_ref)

                configuration = unreal.EditorAssetLibrary.load_asset(configuration_ref)
                configuration.initialize_transient_settings()
                job.set_configuration(configuration)

                workload_good = bool(configuration)

            # mmacieje: QUEUE
            case 2:
                # mmacieje: Load an entire queue asset from the provided reference.
                self.queue = unreal.EditorAssetLibrary.load_asset(queue_ref)
                jobs = self.queue.get_jobs()
                workload_good = bool(jobs)

            case _:
                raise RuntimeError("Unreachable!")

        if workload_good:
            self.start_job_by_index(0)

    @unreal.ufunction(ret=None, params=[int])
    def start_job_by_index(self, idx: int) -> None:
        """
        Starts executing a job from the queue by its index.

        Args:
            idx: The index of the job to start.
        """
        if idx >= len(self.queue.get_jobs()):
            unreal.log_error("Out of Bounds Job Index!")
            self.on_executor_errored_impl()
            return

        self.job_idx = idx

        # mmacieje: Retrieve the map package name associated with the job.
        map_ref = unreal.MoviePipelineLibrary.get_map_package_name(self.queue.get_jobs()[self.job_idx])

        # mmacieje: Optionally, you could load the map here, but this caused me
        # problems
        #
        # begin = unreal.MathLibrary.utc_now()
        # unreal.EditorLoadingAndSavingUtils.load_map(map_ref)
        # end = unreal.MathLibrary.utc_now()
        # split = unreal.MathLibrary.get_total_seconds(unreal.MathLibrary.subtract_date_time_date_time(end, begin))
        #
        # unreal.log(f"Map loaded -> {split} s")

        # mmacieje: Duplicate the selected job into a separate processing queue.
        self.processing_queue = unreal.MoviePipelineQueue()
        job = self.processing_queue.duplicate_job(self.queue.get_jobs()[self.job_idx])

        # mmacieje: Set up the Play In Editor executor for offscreen rendering.
        self.play_in_editor_executor = unreal.MoviePipelinePIEExecutor()
        self.play_in_editor_executor.set_is_rendering_offscreen(1)

        # mmacieje: Register the callback that fires when the individual job finishes.
        self.play_in_editor_executor.on_executor_finished_delegate.add_function_unique(
            self, "on_individual_job_finished"
        )
        self.play_in_editor_executor.execute(self.processing_queue)

    @unreal.ufunction(ret=None, params=[unreal.MoviePipelineExecutorBase, bool])
    def on_individual_job_finished(self, executor: Any, fatal_error: bool) -> None:
        """
        Callback invoked when an individual job finishes.

        Args:
            executor: The executor instance that finished.
            fatal_error: Indicates whether the job finished with a fatal error.
        """
        unreal.log("Job finished! Job Index: " + str(self.job_idx))
        self.processing_queue = None

        # mmacieje: If more jobs remain in the queue, start the next one.
        if self.job_idx < len(self.queue.get_jobs()) - 1:
            self.start_job_by_index(self.job_idx + 1)
        else:
            self.on_executor_finished_impl()

    @unreal.ufunction(override=True)
    def is_rendering(self) -> bool:
        """
        Returns whether rendering is currently in progress.

        Returns:
            True if a Play In Editor executor exists, False otherwise.
        """
        return self.play_in_editor_executor is not None
