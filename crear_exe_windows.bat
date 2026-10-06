@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm MarcaDeAguaInteliun.spec
if errorlevel 1 (
  echo.
  echo ERROR: no se pudo crear el ejecutable.
  pause
  exit /b 1
)
echo.
echo LISTO: dist\MarcaDeAguaInteliun.exe
pause
