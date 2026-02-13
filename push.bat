@echo off
cd /d C:\Users\fraca\Karol-cruscotto-sicilia
git add -A
git commit -m "aggiornamento dashboard %date% %time:~0,5%"
git push
pause
