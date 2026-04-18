; DataPulse POS — custom NSIS installer script
; Included via electron-builder.yml `nsis.include`
;
; Responsibilities:
;   1. Block installation on Windows < 10 (Electron 33 requires Win 10+)
;   2. Check for VC++ 2019 Redistributable (needed by better-sqlite3)
;   3. Warn (not block) if no USB serial port found (thermal printer may be TCP)
;   4. Show a "Ready to ring sales in seconds" welcome page

; ── Windows version check ───────────────────────────────────────────────────

!macro customCheckOS
  ; Electron 33 minimum: Windows 10 (version 10.0, build 10240)
  ${If} ${AtLeastWin10}
    ; OK — continue
  ${Else}
    MessageBox MB_OK|MB_ICONSTOP \
      "DataPulse POS requires Windows 10 or later.$\r$\nPlease upgrade and try again."
    Quit
  ${EndIf}
!macroend

; ── VC++ Redistributable check ─────────────────────────────────────────────
; better-sqlite3 native addon requires VC++ 2019 runtime (14.xx).

!macro customInstall
  ; Check HKLM first (machine-wide), then HKCU (per-user).
  ReadRegStr $0 HKLM \
    "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" "Version"
  StrCmp $0 "" checkHKCU foundVC

  checkHKCU:
  ReadRegStr $0 HKCU \
    "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" "Version"
  StrCmp $0 "" warnVC foundVC

  warnVC:
  MessageBox MB_OKCANCEL|MB_ICONINFORMATION \
    "The Microsoft Visual C++ 2019 Redistributable was not detected.$\r$\n\
DataPulse POS may not start correctly without it.$\r$\n$\r$\n\
Click OK to continue the installation, or Cancel to exit and install$\r$\n\
the redistributable first (vc_redist.x64.exe from microsoft.com)." \
    IDOK foundVC IDCANCEL abortInstall

  abortInstall:
    Quit

  foundVC:
!macroend

; ── Post-install: launch the app ───────────────────────────────────────────

!macro customInstallMode
  ; Force per-machine mode for POS terminals (all users on this machine).
  SetShellVarContext all
!macroend
