#!/bin/bash
# Runs the demo under a virtual screen with a test driver, then upscales its screenshots 3x.
# Usage: tools/test/shoot.sh <driver name without .gd>
cd "$(dirname "$0")/../.."
S="$HOME/.local/share/godot/app_userdata/Miasma II (JRPG demo)/shots"
rm -rf "$S"
timeout ${TIMEOUT:-150} xvfb-run -a -s "-screen 0 960x720x24" godot --path . --rendering-driver opengl3 -- --driver=res://tools/test/$1.gd 2>&1 | grep -E "SHOT|ERROR|SCRIPT|LOG" | grep -v ALSA | grep -v "audio_driver\|ERR_CANT_OPEN"
OUT=${OUT:-/tmp/shots}; mkdir -p $OUT
python3 -c "
import glob,os
from PIL import Image
for f in glob.glob('''$S/*.png'''):
    im=Image.open(f); im.resize((im.width*3,im.height*3),Image.NEAREST).save('$OUT/'+os.path.basename(f))
"
