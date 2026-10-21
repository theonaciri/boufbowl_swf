; Single-download launcher; the payload stays cached between launches.
Unicode true
Name "Boufbowl Fan"
Icon "${APP_ICON}"
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "Boufbowl Fan"
VIAddVersionKey "FileDescription" "Boufbowl Fan"
VIAddVersionKey "FileVersion" "1.0.0"
OutFile "${OUTPUT_FILE}"
RequestExecutionLevel user
SilentInstall silent
AutoCloseWindow true
SetCompressor /SOLID lzma
SetDatablockOptimize on

Function .onInit
  SetShellVarContext current
  StrCpy $INSTDIR "$LOCALAPPDATA\Boufbowl\player\${BUNDLE_REVISION}"
FunctionEnd

Section
  IfFileExists "$INSTDIR\.complete" 0 unpack
  IfFileExists "$INSTDIR\flashplayer.exe" 0 unpack
  IfFileExists "$INSTDIR\bin\boufbowl-client-1.9.6.swf" launch unpack
unpack:
  SetOutPath "$INSTDIR"
  SetOverwrite on
  ClearErrors
  File /r "${PAYLOAD_DIR}/*"
  IfErrors failed
  FileOpen $0 "$INSTDIR\.complete" w
  IfErrors failed
  FileWrite $0 "${BUNDLE_REVISION}"
  FileClose $0
launch:
  SetOutPath "$INSTDIR"
  ; nsExec keeps the CMD helper hidden and waits until Flash closes.
  nsExec::ExecToStack '"$SYSDIR\cmd.exe" /d /s /c ""$INSTDIR\Jouer.cmd""'
  Pop $0
  Pop $1
  StrCmp $0 "0" done
  MessageBox MB_OK|MB_ICONSTOP "Impossible de lancer Boufbowl Fan ($0).$\r$\n$1"
  SetErrorLevel 1
  Goto done
failed:
  MessageBox MB_OK|MB_ICONSTOP "Impossible de preparer les fichiers de Boufbowl Fan dans $INSTDIR."
  SetErrorLevel 1
done:
SectionEnd
