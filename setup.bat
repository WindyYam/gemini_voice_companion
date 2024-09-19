python -m pip install virtualenv
python -m venv .venv
"./.venv/Scripts/python" -m pip install -r requirements.txt
"./.venv/Scripts/python" -m pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
pause