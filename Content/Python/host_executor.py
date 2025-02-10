from typing import Any, Dict, List
import unreal

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

SEQUENCE: int = 0
CONFIGURATION: int = 1
QUEUE: int = 2

@unreal.uclass()
class HostExecutor(unreal.MoviePipelinePythonHostExecutor):
    job_idx = unreal.uproperty(int)
    queue_that_is_constructed = unreal.uproperty(unreal.MoviePipelineQueue)
    queue_that_is_processed = unreal.uproperty(unreal.MoviePipelineQueue)
    pie_executor_that_truly_executes = unreal.uproperty(unreal.MoviePipelinePIEExecutor)

    def _post_init(self) -> None:
        self.job_idx = -1
        self.queue_that_is_constructed = None
        self.queue_that_is_processed = None
        self.pie_executor_that_truly_executes = None

    @unreal.ufunction(override=True)
    def is_rendering(self) -> bool:
        return bool(self.pie_executor_that_truly_executes)

    @unreal.ufunction(override=True)
    def on_begin_frame(self) -> None:
        super(HostExecutor, self).on_begin_frame()

        # NOTE(mmacieje): `active_movie_pipeline` property is `Transient`, not
        # `BlueprintReadWrite` and thus cannot be used here; you may want to
        # modify its kind in `MoviePipelineLinearExecutor.h` file.
        #
        #     movie_pipeline = self.pie_executor_that_truly_executes.active_movie_pipeline
        #     if movie_pipeline:
        #         pipeline_state = unreal.MoviePipelineLibrary.get_pipeline_state(movie_pipeline)
        #         shot_state = unreal.MoviePipelineLibrary.get_current_segment_state(movie_pipeline)
        #         if pipeline_state == unreal.MovieRenderPipelineState.PRODUCING_FRAMES and shot_state == unreal.MovieRenderShotState.RENDERING:
        #             metrics = unreal.MoviePipelineLibrary.get_current_segment_work_metrics(movie_pipeline)
        #             frame_idx, frame_count = unreal.MoviePipelineLibrary.get_overall_output_frames(movie_pipeline)
        #             aa_setting = unreal.MoviePipelineLibrary.find_or_get_default_setting_for_shot(unreal.MoviePipelineAntiAliasingSetting, movie_pipeline.get_pipeline_primary_config(), unreal.MoviePipelineLibrary.get_current_executor_shot(movie_pipeline))
        #             spatial_sample_count = aa_setting.spatial_sample_count 
        #             sub_sample_idx = metrics.output_sub_sample_index + spatial_sample_count + 1
        #             sub_sample_count = metrics.total_sub_sample_count
        #             unreal.log(f"Sample -> ({frame_idx}/{frame_count}) ~ Sub-sample -> [{sub_sample_idx}/{sub_sample_count}]")
        #

    @unreal.ufunction(override=True)
    def execute_delayed(self, queue: Any) -> None:
        _ = queue

        # mmacieje: Parse the command line into tokens, switches, and arguments
        cmdln_tokens, cmdln_switches, cmdln_args = unreal.SystemLibrary.parse_command_line(unreal.SystemLibrary.get_command_line())

        def find_needle(haysack: List[Any], needle: Any) -> bool:
            result = False
            for item in haysack:
                if item == needle:
                    result = True
                    break
            return result

        # mmacieje: Extract command-line arguments, converting to proper types and providing defaults
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

        # mmacieje: Determine the type of workload based on which command-line arguments are provided
        workload_kind: int = -1
        if sequence_ref:
            workload_kind = SEQUENCE
        if configuration_ref:
            workload_kind = CONFIGURATION
        if queue_ref:
            workload_kind = QUEUE

        workload_good: bool = False

        # mmacieje: Configure the rendering job based on the workload type
        match workload_kind:
            # mmacieje: SEQUENCE
            case 0:
                # mmacieje: Create a new movie pipeline queue and allocate a job
                self.queue_that_is_constructed = unreal.MoviePipelineQueue()
                job = self.queue_that_is_constructed.allocate_new_job()

                # mmacieje: Set metadata and asset references for the job
                job.comment = "Install and repair pipes and fixtures that carry water, gas, or other fluids in homes and businesses"
                job.job_name = "Plumber"
                job.map = unreal.SoftObjectPath(map_ref)
                job.sequence = unreal.SoftObjectPath(sequence_ref)

                configuration = job.get_configuration()

                # mmacieje: High-resolution rendering settings
                high_resolution_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineHighResSetting)
                high_resolution_setting.allocate_history_per_tile = True
                high_resolution_setting.burley_sample_count = 64
                high_resolution_setting.overlap_ratio = 0
                high_resolution_setting.override_sub_surface_scattering = True
                high_resolution_setting.texture_sharpness_bias = 0
                high_resolution_setting.tile_count = 1

                # mmacieje: Output settings
                output_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
                output_setting.use_custom_playback_range = start_frame != -1 and end_frame != -1
                output_setting.custom_end_frame = end_frame
                output_setting.custom_start_frame = start_frame
                output_setting.output_resolution = unreal.IntPoint(width, height)
                output_setting.use_custom_frame_rate = True
                output_setting.output_frame_rate = unreal.FrameRate(numerator=frame_rate)
                output_setting.zero_pad_frame_numbers = 4
                output_setting.output_directory = unreal.DirectoryPath(path=f"{{project_dir}}/Saved/MovieRenders/{{output_resolution}}_{{ts_count}}_{{ss_count}}_{frame_rate}_{deferred_pass}")
                output_setting.file_name_format = f"{{render_pass}}/{{frame_number}}"

                # mmacieje: Configure the deferred pass settings
                deferred_pass_obj = configuration.find_or_add_setting_by_class(deferred_passes_name_type_dict[deferred_pass])
                material_name_list: List[str] = [item.strip() for item in materials.split(",") if item.strip()]
                material_ref_list: List[str] = []
                for material_name in material_name_list:
                    material_ref = materials_name_ref_dict.get(material_name.lower())
                    if material_ref:
                        material_ref_list.append(material_ref)

                # mmacieje: For each material reference, add a post process pass to the deferred pass
                for material_ref in material_ref_list:
                    post_process_pass = unreal.MoviePipelinePostProcessPass()
                    post_process_pass.enabled = True
                    post_process_pass.material = unreal.load_asset(material_ref)
                    deferred_pass_obj.additional_post_process_materials.append(post_process_pass)

                deferred_pass_obj.disable_multisample_effects = True
                deferred_pass_obj.render_main_pass = True

                # mmacieje: Anti-aliasing settings
                anti_aliasing_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
                anti_aliasing_setting.anti_aliasing_method = unreal.AntiAliasingMethod.AAM_NONE
                anti_aliasing_setting.engine_warm_up_count = engine_warm_up_count
                anti_aliasing_setting.override_anti_aliasing = True
                anti_aliasing_setting.render_warm_up_count = render_warm_up_count
                anti_aliasing_setting.render_warm_up_frames = True
                anti_aliasing_setting.spatial_sample_count = spatial_sample_count
                anti_aliasing_setting.temporal_sample_count = temporal_sample_count
                anti_aliasing_setting.use_camera_cut_for_warm_up = False

                # mmacieje: EXR image sequence output settings
                exr_output_configuration = configuration.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_EXR)
                exr_output_configuration.compression = unreal.EXRCompressionFormat.PIZ
                total_sample_count_threshold: int = 128
                if spatial_sample_count * temporal_sample_count == total_sample_count_threshold:
                    exr_output_configuration.compression = unreal.EXRCompressionFormat.ZIP
                exr_output_configuration.multilayer = multilayer

                # mmacieje: Console variable settings
                console_variable_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
                for console_var, value in console_vars_name_value_dict.items():
                    console_variable_setting.add_or_update_console_variable(console_var, value)

                # mmacieje: Game override settings
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

                # mmacieje: Initialize any transient settings and assign the configuration
                configuration.initialize_transient_settings()
                job.set_configuration(configuration)

                workload_good = True

            # mmacieje: CONFIGURATION
            case 1:
                # mmacieje: Create a new job and load a pre-existing configuration asset
                self.queue_that_is_constructed = unreal.MoviePipelineQueue()
                job = self.queue_that_is_constructed.allocate_new_job()
                job.comment = "Measure, cut, and shape wood, plastic, and other materials"
                job.job_name = "Carpenter"
                job.map = unreal.SoftObjectPath(map_ref)
                job.sequence = unreal.SoftObjectPath(sequence_ref)

                configuration = unreal.EditorAssetLibrary.load_asset(configuration_ref)
                configuration.initialize_transient_settings()
                job.set_configuration(configuration)

                workload_good = bool(configuration)

            # mmacieje: QUEUE
            case 2:
                # mmacieje: Load an entire queue asset from the provided reference
                self.queue_that_is_constructed = unreal.EditorAssetLibrary.load_asset(queue_ref)
                jobs = self.queue_that_is_constructed.get_jobs()
                workload_good = bool(jobs)

            case _:
                raise RuntimeError("Unreachable!")

        # (*) In `kickoff.py` I mentioned that `user_data` could be whatever
        # and thus, we are about to serialise a `struct` into it and
        # deserialise it later in the process, just to prove it works and to
        # tackle a problem with Movie Pipeline itself.
        unreal.log(f"This i.e. `user_data` was: '{self.user_data}'.")
        self.user_data = repr(workload_kind)
        unreal.log(f"Now, it is: '{self.user_data}'.")

        if workload_good:
            self.start_job_by_index(0)

    @unreal.ufunction(ret=None, params=[int])
    def start_job_by_index(self, idx: int) -> None:
        if idx >= len(self.queue_that_is_constructed.get_jobs()):
            unreal.log_error("Out of Bounds Job Index!")
            self.on_executor_errored_impl()
            return

        self.job_idx = idx

        # NOTE (mmacieje): Since the usual workflow of this implementation of
        # an Python Host Executor involves rendering a single Queue containing
        # only one Job, loading a map here makes little sense. However, in
        # scenarios where the Queue is defined externally (for example, by you
        # or someone else who believed this would be a good idea), you might
        # have to handle such cases. Therefore, this situation is addressed
        # here, although bear in mind that it might cause world memory leaks
        # for reasons that remain unclear. Collecting _the_ garbage both on
        # this side and on the editor's side is of little use.
        #
        # (*) Alright, fiddling with `user_data` continued
        workload_kind = eval(self.user_data)
        if workload_kind == QUEUE:
            # mmacieje: Retrieve the map package name associated with the job
            map_ref = unreal.MoviePipelineLibrary.get_map_package_name(self.queue_that_is_constructed.get_jobs()[self.job_idx])

            unreal.EditorLoadingAndSavingUtils.load_map(map_ref)

        # mmacieje: Duplicate the selected job into a separate processing queue
        self.queue_that_is_processed = unreal.MoviePipelineQueue()
        job = self.queue_that_is_processed.duplicate_job(self.queue_that_is_constructed.get_jobs()[self.job_idx])

        # mmacieje: Set up the Play In Editor executor for offscreen rendering
        self.pie_executor_that_truly_executes = unreal.MoviePipelinePIEExecutor()
        self.pie_executor_that_truly_executes.set_is_rendering_offscreen(1)

        # mmacieje: Register the callback that fires when the individual job finishes
        self.pie_executor_that_truly_executes.http_response_recieved_delegate
        self.pie_executor_that_truly_executes.on_executor_errored_delegate
        self.pie_executor_that_truly_executes.on_executor_finished_delegate.add_function_unique(self, "on_individual_job_finished")
        self.pie_executor_that_truly_executes.on_individual_job_started_delegate
        self.pie_executor_that_truly_executes.on_individual_job_work_finished_delegate
        self.pie_executor_that_truly_executes.on_individual_shot_work_finished_delegate
        self.pie_executor_that_truly_executes.socket_message_recieved_delegate
        self.pie_executor_that_truly_executes.target_pipeline_class
        self.pie_executor_that_truly_executes.user_data

        self.pie_executor_that_truly_executes.execute(self.queue_that_is_processed)

    @unreal.ufunction(ret=None, params=[unreal.MoviePipelineExecutorBase, bool])
    def on_individual_job_finished(self, executor: Any, fatal_error: bool) -> None:
        unreal.log("Job finished! Job Index: " + str(self.job_idx))
        self.queue_that_is_processed = None

        # mmacieje: If more jobs remain in the queue, start the next one
        if self.job_idx < len(self.queue_that_is_constructed.get_jobs()) - 1:
            self.start_job_by_index(self.job_idx + 1)
        else:
            self.on_executor_finished_impl()

