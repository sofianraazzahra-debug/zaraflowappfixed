[app]

title = Zaraflow
package.name = zaraflow
package.domain = org.zaraflow

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,ttf,otf,txt
source.exclude_exts = db,pyc,pyo,pyd
version = 0.1

requirements = python3,kivy==2.3.1,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS
android.api = 34
android.minapi = 23
android.archs = arm64-v8a

[buildozer]

log_level = 2
warn_on_root = 0
