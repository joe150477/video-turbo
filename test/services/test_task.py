import unittest
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import task as tm
from app.models.schema import MaterialInfo, VideoParams
from app.utils import utils

resources_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
RUN_INTEGRATION_TESTS = os.environ.get("MPT_RUN_INTEGRATION_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
}


class TestTaskService(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_generate_script_forwards_advanced_prompt_options(self):
        """
        任务生成入口和 WebUI/API 共用 VideoParams。这里验证自动生成文案时，
        高级提示词参数会继续传到 LLM 服务层，避免只在 /scripts 接口生效。
        """
        params = VideoParams(
            video_subject="咖啡",
            video_script="",
            video_language="zh-CN",
            paragraph_number=2,
            video_script_prompt="语气轻松",
            custom_system_prompt="Only write short narration.",
        )

        with patch.object(tm.llm, "generate_script", return_value="生成的文案") as generate:
            result = tm.generate_script("task-id", params)

        self.assertEqual(result, "生成的文案")
        generate.assert_called_once_with(
            video_subject="咖啡",
            language="zh-CN",
            paragraph_number=2,
            video_script_prompt="语气轻松",
            custom_system_prompt="Only write short narration.",
        )

    def test_persuasive_chain_runs_when_brand_context_present_without_manual_prompt(self):
        """
        Con contexto de marca y modo persuasivo activo, el cerebro persuasivo
        (script_studio) debe ejecutarse; el contexto de marca ya NO llega como
        video_script_prompt, así que no debe caer en el camino clásico.
        """
        params = VideoParams(
            video_subject="curso de inglés",
            video_script="",
            video_language="es",
        )
        brand = {
            "persuasive_mode": True,
            "brand_context": "Academia bilingüe en Barranquilla",
            "target_audience": "padres de familia",
            "role_models": None,
        }

        with (
            patch.object(tm.setup, "get_brand_settings", return_value=brand),
            patch.object(
                tm, "_generate_persuasive_script", return_value="guion persuasivo"
            ) as persuasive,
            patch.object(tm.llm, "generate_script") as classic,
        ):
            result = tm.generate_script("task-id", params)

        self.assertEqual(result, "guion persuasivo")
        persuasive.assert_called_once_with(params, brand)
        classic.assert_not_called()

    def test_classic_path_falls_back_to_brand_context_when_persuasive_off(self):
        """
        Con el modo persuasivo apagado y sin prompt manual, el camino clásico
        debe inyectar el contexto de marca como video_script_prompt para que la
        voz de marca no se pierda.
        """
        params = VideoParams(
            video_subject="curso de inglés",
            video_script="",
            video_language="es",
        )
        brand = {
            "persuasive_mode": False,
            "brand_context": "Academia bilingüe en Barranquilla",
        }

        with (
            patch.object(tm.setup, "get_brand_settings", return_value=brand),
            patch.object(tm.llm, "generate_script", return_value="guion clásico") as classic,
        ):
            result = tm.generate_script("task-id", params)

        self.assertEqual(result, "guion clásico")
        classic.assert_called_once_with(
            video_subject="curso de inglés",
            language="es",
            paragraph_number=1,
            video_script_prompt="Academia bilingüe en Barranquilla",
            custom_system_prompt="",
        )

    def test_generate_terms_uses_script_order_mode_when_enabled(self):
        """
        默认模式不受影响；只有用户显式开启素材按文案顺序匹配时，任务层才
        要求 LLM 生成有序关键词，并适当增加关键词数量以覆盖更多脚本片段。
        """
        params = VideoParams(
            video_subject="城市通勤",
            video_script="",
            match_materials_to_script=True,
        )

        with patch.object(tm.llm, "generate_terms", return_value=["city", "train"]) as generate:
            result = tm.generate_terms("task-id", params, "先城市，再地铁")

        self.assertEqual(result, ["city", "train"])
        generate.assert_called_once_with(
            video_subject="城市通勤",
            video_script="先城市，再地铁",
            amount=8,
            match_script_order=True,
        )

    def test_generate_audio_uses_custom_file_inside_task_directory(self):
        task_id = "test-custom-audio-safe"
        task_dir = utils.task_dir(task_id)
        custom_audio_file = os.path.join(task_dir, "custom-audio.mp3")
        with open(custom_audio_file, "wb") as audio:
            audio.write(b"fake audio")

        params = VideoParams(
            video_subject="custom audio",
            video_script="",
            custom_audio_file=custom_audio_file,
            voice_name="test-voice",
        )

        try:
            with (
                patch.object(tm.voice, "tts") as tts,
                patch.object(tm.voice, "get_audio_duration", return_value=7),
            ):
                audio_file, audio_duration, sub_maker = tm.generate_audio(task_id, params, "script")
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

        self.assertEqual(audio_file, os.path.realpath(custom_audio_file))
        self.assertEqual(audio_duration, 7)
        self.assertIsNone(sub_maker)
        tts.assert_not_called()

    def test_generate_audio_accepts_server_side_custom_file(self):
        task_id = "test-custom-audio-server-side"
        task_dir = utils.task_dir(task_id)

        with tempfile.NamedTemporaryFile(suffix=".mp3") as server_audio:
            server_audio.write(b"fake audio")
            server_audio.flush()
            params = VideoParams(
                video_subject="custom audio",
                video_script="",
                custom_audio_file=server_audio.name,
                voice_name="test-voice",
            )

            try:
                with (
                    patch.object(tm.voice, "tts") as tts,
                    patch.object(tm.voice, "get_audio_duration", return_value=6),
                ):
                    audio_file, audio_duration, result_sub_maker = tm.generate_audio(
                        task_id, params, "script"
                    )
            finally:
                shutil.rmtree(task_dir, ignore_errors=True)

        self.assertEqual(audio_file, os.path.realpath(server_audio.name))
        self.assertEqual(audio_duration, 6)
        self.assertIsNone(result_sub_maker)
        tts.assert_not_called()

    def test_generate_audio_rejects_missing_custom_file_without_tts(self):
        task_id = "test-custom-audio-missing"
        task_dir = utils.task_dir(task_id)
        missing_audio_file = os.path.join(task_dir, "missing.mp3")
        params = VideoParams(
            video_subject="custom audio",
            video_script="",
            custom_audio_file=missing_audio_file,
            voice_name="test-voice",
        )

        try:
            with (
                patch.object(tm.voice, "tts") as tts,
                patch.object(tm.sm.state, "update_task") as update_task,
            ):
                audio_file, audio_duration, result_sub_maker = tm.generate_audio(
                    task_id, params, "script"
                )
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

        self.assertIsNone(audio_file)
        self.assertIsNone(audio_duration)
        self.assertIsNone(result_sub_maker)
        tts.assert_not_called()
        update_task.assert_called_with(task_id, state=tm.const.TASK_STATE_FAILED)

    def test_generate_subtitle_uses_whisper_for_custom_audio_without_sub_maker(self):
        """
        自定义音频不会经过 TTS，所以没有 sub_maker。
        Whisper 可以直接从音频文件转写，此时不能被 sub_maker 为空的保护逻辑提前跳过。
        """
        task_id = "test-custom-audio-whisper-subtitle"
        task_dir = utils.task_dir(task_id)
        audio_file = os.path.join(task_dir, "custom-audio.mp3")
        Path(audio_file).write_bytes(b"fake audio")
        params = VideoParams(
            video_subject="custom audio",
            video_script="Hello world.",
            subtitle_enabled=True,
        )

        def fake_whisper_create(audio_file, subtitle_file):
            Path(subtitle_file).write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nHello world.\n\n",
                encoding="utf-8",
            )

        try:
            with (
                patch.object(
                    tm.config,
                    "app",
                    dict(tm.config.app, subtitle_provider="whisper"),
                ),
                patch.object(tm.subtitle, "create", side_effect=fake_whisper_create) as create,
                patch.object(tm.subtitle, "correct") as correct,
            ):
                subtitle_path = tm.generate_subtitle(
                    task_id=task_id,
                    params=params,
                    video_script="Hello world.",
                    sub_maker=None,
                    audio_file=audio_file,
                )
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

        self.assertTrue(subtitle_path.endswith("subtitle.srt"))
        create.assert_called_once_with(audio_file=audio_file, subtitle_file=subtitle_path)
        correct.assert_called_once_with(subtitle_file=subtitle_path, video_script="Hello world.")

    def test_generate_subtitle_skips_edge_provider_without_sub_maker(self):
        """
        Edge 字幕依赖 TTS 返回的 sub_maker 时间轴。
        自定义音频缺少该对象时应继续跳过，避免产生不可信的字幕时间轴。
        """
        task_id = "test-custom-audio-edge-no-submaker"
        task_dir = utils.task_dir(task_id)
        audio_file = os.path.join(task_dir, "custom-audio.mp3")
        Path(audio_file).write_bytes(b"fake audio")
        params = VideoParams(
            video_subject="custom audio",
            video_script="Hello world.",
            subtitle_enabled=True,
        )

        try:
            with (
                patch.object(
                    tm.config,
                    "app",
                    dict(tm.config.app, subtitle_provider="edge"),
                ),
                patch.object(tm.voice, "create_subtitle") as create_subtitle,
                patch.object(tm.subtitle, "create") as whisper_create,
            ):
                subtitle_path = tm.generate_subtitle(
                    task_id=task_id,
                    params=params,
                    video_script="Hello world.",
                    sub_maker=None,
                    audio_file=audio_file,
                )
        finally:
            shutil.rmtree(task_dir, ignore_errors=True)

        self.assertEqual(subtitle_path, "")
        create_subtitle.assert_not_called()
        whisper_create.assert_not_called()

    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_task_local_materials(self):
        task_id = "00000000-0000-0000-0000-000000000000"
        video_materials = []
        for i in range(1, 4):
            video_materials.append(
                MaterialInfo(
                    provider="local", url=os.path.join(resources_dir, f"{i}.png"), duration=0
                )
            )

        params = VideoParams(
            video_subject="金钱的作用",
            video_script="金钱不仅是交换媒介，更是社会资源的分配工具。它能满足基本生存需求，如食物和住房，也能提供教育、医疗等提升生活品质的机会。拥有足够的金钱意味着更多选择权，比如职业自由或创业可能。但金钱的作用也有边界，它无法直接购买幸福、健康或真诚的人际关系。过度追逐财富可能导致价值观扭曲，忽视精神层面的需求。理想的状态是理性看待金钱，将其作为实现目标的工具而非终极目的。",
            video_terms="money importance, wealth and society, financial freedom, money and happiness, role of money",
            video_aspect="9:16",
            video_concat_mode="random",
            video_transition_mode="None",
            video_clip_duration=3,
            video_count=1,
            video_source="local",
            video_materials=video_materials,
            video_language="",
            voice_name="zh-CN-XiaoxiaoNeural-Female",
            voice_volume=1.0,
            voice_rate=1.0,
            bgm_type="random",
            bgm_file="",
            bgm_volume=0.2,
            subtitle_enabled=True,
            subtitle_position="bottom",
            custom_position=70.0,
            font_name="MicrosoftYaHeiBold.ttc",
            text_fore_color="#FFFFFF",
            text_background_color=True,
            font_size=60,
            stroke_color="#000000",
            stroke_width=1.5,
            n_threads=2,
            paragraph_number=1,
        )
        result = tm.start(task_id=task_id, params=params)
        print(result)

    def test_own_materials_topped_up_with_stock_when_enabled(self):
        """With supplement_with_stock on, own clips are kept AND stock is
        appended so a small personal library still fills the video."""
        params = VideoParams(
            video_subject="colegio",
            video_source="local",
            video_materials=[MaterialInfo(provider="local", url="campus.mp4")],
            supplement_with_stock=True,
            fallback_source="pexels",
        )
        own = [MaterialInfo(provider="local", url="campus.mp4")]
        with (
            patch.object(tm.video, "preprocess_video", return_value=own),
            patch.object(
                tm.material, "download_videos", return_value=["/stock/clip1.mp4"]
            ) as download,
        ):
            result = tm.get_video_materials(
                "task-mix", params, video_terms=["Barranquilla"], audio_duration=30
            )

        self.assertEqual(result, ["campus.mp4", "/stock/clip1.mp4"])
        download.assert_called_once()

    def test_own_materials_alone_when_supplement_disabled(self):
        params = VideoParams(
            video_subject="colegio",
            video_source="local",
            video_materials=[MaterialInfo(provider="local", url="campus.mp4")],
            supplement_with_stock=False,
        )
        own = [MaterialInfo(provider="local", url="campus.mp4")]
        with (
            patch.object(tm.video, "preprocess_video", return_value=own),
            patch.object(tm.material, "download_videos") as download,
        ):
            result = tm.get_video_materials("task-own", params, video_terms=[], audio_duration=30)

        self.assertEqual(result, ["campus.mp4"])
        download.assert_not_called()

    def test_stock_failure_does_not_sink_own_materials(self):
        params = VideoParams(
            video_subject="colegio",
            video_source="local",
            video_materials=[MaterialInfo(provider="local", url="campus.mp4")],
            supplement_with_stock=True,
            fallback_source="pexels",
        )
        own = [MaterialInfo(provider="local", url="campus.mp4")]
        with (
            patch.object(tm.video, "preprocess_video", return_value=own),
            patch.object(tm.material, "download_videos", side_effect=RuntimeError("network")),
        ):
            result = tm.get_video_materials(
                "task-mixfail", params, video_terms=["Barranquilla"], audio_duration=30
            )

        self.assertEqual(result, ["campus.mp4"])

    def test_start_tags_processing_checkpoints_with_a_stage(self):
        """The desktop UI checklist needs a named stage per checkpoint, not
        just a bare percentage, to know which step is currently running."""
        params = VideoParams(video_subject="test", video_source="local")

        with (
            patch.object(tm.sm, "state") as state,
            patch.object(tm, "generate_script", return_value="a script"),
        ):
            tm.start(task_id="task-stage", params=params, stop_at="script")

        stages = [
            call.kwargs.get("stage")
            for call in state.update_task.call_args_list
            if "stage" in call.kwargs
        ]
        self.assertIn("script", stages)

    def test_start_marks_task_failed_with_translated_message_on_unexpected_error(self):
        """If a pipeline step raises something nobody anticipated (a bug, a
        missing system dependency, an unhandled provider error), the task
        must still end up FAILED with a user-facing message — never stuck at
        "processing" forever, since the background thread would otherwise
        just die silently and leave the UI polling indefinitely."""
        params = VideoParams(video_subject="test", video_source="local")

        with (
            patch.object(tm.sm, "state") as state,
            patch.object(tm, "generate_script", side_effect=RuntimeError("boom")),
        ):
            result = tm.start(task_id="task-crash", params=params)

        self.assertIsNone(result)
        failed_calls = [
            call
            for call in state.update_task.call_args_list
            if call.kwargs.get("state") == tm.const.TASK_STATE_FAILED
        ]
        self.assertTrue(failed_calls)
        last_failed_call = failed_calls[-1]
        self.assertIn("error_message", last_failed_call.kwargs)
        self.assertIn("error_code", last_failed_call.kwargs)


if __name__ == "__main__":
    unittest.main()
