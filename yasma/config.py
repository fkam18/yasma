import os
from pathlib import Path
import toml
from dataclasses import dataclass, field
from typing import List, Optional, Dict

CONFIG_PATH = Path(os.environ.get("YASMA_CONFIG", "/app/config.toml"))

@dataclass
class PluginDef:
    script: str
    config: str = ""

@dataclass
class YapoConfig:
    url: str
    api_token: str
    default_model: str = "yasma"

@dataclass
class DefaultsConfig:
    title: str = "Check it out"          # new
    vibe: str = "documentary"
    hints: str = "Today, UK, Event"      # new
    categories: List[str] = field(default_factory=lambda: ["general"])
    length: str = "short"
    use_exif: bool = True
    model: str = "yasma"
    post_plugins: List[str] = field(default_factory=lambda: ["wordpress"]) 

@dataclass
class AppConfig:
    processing_times: List[str] = field(default_factory=lambda: ["10:00", "15:00", "22:00"])
    yapo: YapoConfig = None
    job_queue_root: str = "/data/jobs"
    auto_approve: bool = False
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    allowed_categories: List[str] = field(default_factory=lambda: ["general", "food", "travel", "event", "nature", "tech"])
    plugins: Dict[str, PluginDef] = field(default_factory=dict)

def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    data = toml.load(CONFIG_PATH)

    # --- LLM / YAPO config ---
    yapo_data = data.get("yapo", {})
    yapo = YapoConfig(
        url=yapo_data.get("url", ""),
        api_token=yapo_data.get("api_token", ""),
        default_model=yapo_data.get("default_model", "yasma"),
    )

    # --- Defaults ---
    defaults_data = data.get("defaults", {})
    defaults = DefaultsConfig(
        title=defaults_data.get("title", "Check it out"),
        vibe=defaults_data.get("vibe", "documentary"),
        hints=defaults_data.get("hints", "Today, UK, Event"),
        categories=defaults_data.get("categories", ["general"]),
        length=defaults_data.get("length", "short"),
        use_exif=defaults_data.get("use_exif", True),
        model=defaults_data.get("model", "yasma"),
        post_plugins=defaults_data.get("post_plugins", ["wordpress"]),
    )

    # --- Plugins (parse to PluginDef) ---
    plugins_raw = data.get("plugins", {})
    plugins = {}
    for name, value in plugins_raw.items():
        if isinstance(value, str):
            plugins[name] = PluginDef(script=value)
        elif isinstance(value, dict):
            plugins[name] = PluginDef(
                script=value.get("script", ""),
                config=value.get("config", ""),
            )

    # --- Allowed categories ---
    allowed_categories = data.get(
        "allowed_categories",
        ["general", "food", "travel", "event", "nature", "tech"],
    )

    # --- Build the final AppConfig ---
    config = AppConfig(
        processing_times=data.get("processing_times", ["10:00", "15:00", "22:00"]),
        yapo=yapo,
        job_queue_root=data.get("job_queue_root", "/data/jobs"),
        auto_approve=data.get("auto_approve", False),
        defaults=defaults,
        allowed_categories=allowed_categories,
        plugins=plugins,
    )
    return config

def save_config(config: AppConfig):
    data = {
        "processing_times": config.processing_times,
        "yapo": {
            "url": config.yapo.url,
            "api_token": config.yapo.api_token,
            "default_model": config.yapo.default_model,
        },
        "job_queue_root": config.job_queue_root,
        "auto_approve": config.auto_approve,
        "defaults": {
            "title": config.defaults.title,
            "vibe": config.defaults.vibe,
            "hints": config.defaults.hints,
            "categories": config.defaults.categories,
            "length": config.defaults.length,
            "use_exif": config.defaults.use_exif,
            "model": config.defaults.model,
            "post_plugins": config.defaults.post_plugins,
        },
        "allowed_categories": config.allowed_categories,
        "plugins": {
            name: {"script": p.script, "config": p.config}
            for name, p in config.plugins.items()
        },
    }
    with open(CONFIG_PATH, "w") as f:
        toml.dump(data, f)

