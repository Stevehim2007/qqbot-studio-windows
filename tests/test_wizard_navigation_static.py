"""Static/logic checks for the App nav and task-96 wizard step lock."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "windows"
STATIC = ROOT / "qqbot_studio" / "static"


def _extract_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    quote = ""
    escaped = False
    index = brace
    while index < len(source):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        else:
            if char in ("'", '"', "`"):
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index + 1]
        index += 1
    raise AssertionError(f"could not extract {name}")


class WizardNavigationStaticTests(unittest.TestCase):
    def test_task96_step_picker_and_lock_markup(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        css = (STATIC / "styles.css").read_text(encoding="utf-8")
        for marker in (
            'id="wizard-step-select"',
            'id="wizard-step-lock-note"',
            "1. 检查环境",
            "2. 账号与模型",
            "3. 部署进度",
            "4. 完成与运行",
        ):
            self.assertIn(marker, html)
        for marker in (
            "function deploymentStepsLocked",
            "deployment.deployed === true || app.jobCompleted === true",
            "return step === 'done'",
            "机器人已部署，环境/账号/部署步骤已锁定",
            "stepSelect.addEventListener('change'",
            "app.jobCompleted",
        ):
            self.assertIn(marker, js)
        self.assertIn(".wizard-step-select", css)

    def test_locked_logic_allows_only_done_after_deploy(self) -> None:
        if not shutil.which("node"):
            self.skipTest("node is not installed")
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        functions = "\n\n".join(
            _extract_function(js, name)
            for name in ("deploymentStepsLocked", "isStepAvailable")
        )
        prelude = r"""
        const STEP_META = {env:{},config:{},deploy:{},done:{}};
        const app = {currentStep:'config',jobCompleted:false,state:{deployment:{deployed:false}}};
        const steps = ['env','config','deploy','done'];
        const unlocked = Object.fromEntries(steps.map((step)=>[step,isStepAvailable(step)]));
        app.state.deployment.deployed = true;
        const deployed = Object.fromEntries(steps.map((step)=>[step,isStepAvailable(step)]));
        app.state.deployment.deployed = false;
        app.jobCompleted = true;
        const completed = Object.fromEntries(steps.map((step)=>[step,isStepAvailable(step)]));
        console.log(JSON.stringify({unlocked,deployed,completed}));
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "wizard-lock.js"
            path.write_text(prelude + "\n" + functions, encoding="utf-8")
            result = subprocess.run(["node", str(path)], check=True, capture_output=True, text=True)
        data = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(set(data["unlocked"].values()), {True})
        for key in ("deployed", "completed"):
            for step in ("env", "config", "deploy"):
                self.assertFalse(data[key][step], f"{key} {step}")
            self.assertTrue(data[key]["done"], f"{key} done")

    def test_app_shell_has_console_and_wizard_navigation(self) -> None:
        source = (WINDOWS / "app_shell.py").read_text(encoding="utf-8")
        for marker in (
            "_APP_NAV_JS",
            "QQ Bot Studio App 导航",
            "控制台",
            "向导",
            "data-qb-nav=\"console\"",
            "data-qb-nav=\"wizard\"",
            "'/api/instances'",
            "'/wizard?instance='",
            "window.location.assign",
        ):
            self.assertIn(marker, source)

    def test_native_dashboard_has_nav_and_wizard_step_lock(self) -> None:
        source = (WINDOWS / "native_app.py").read_text(encoding="utf-8")
        for marker in (
            'id="native-app-nav"',
            'data-native-nav="console"',
            'data-native-nav="wizard"',
            'id="native-wizard-step-select"',
            'id="native-wizard-lock-note"',
            "1. 检查环境",
            "2. 安装组件",
            "3. 配置与启动",
            "4. 完成与人工验证",
            "function deployedEnv",
            "function updateWizardLock",
            "option.disabled=locked&&option.value!=='done'",
            "只能进入完成与人工验证",
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
