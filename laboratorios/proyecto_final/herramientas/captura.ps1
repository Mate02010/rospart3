param(
  [Parameter(Mandatory=$true)][string]$Titulo,
  [Parameter(Mandatory=$true)][string]$Salida,
  [switch]$Listar
)
# Captura una ventana por su título sin traerla al frente (PrintWindow con PW_RENDERFULLCONTENT).
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Text;
public class Cap {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  public static List<KeyValuePair<IntPtr,string>> Ventanas() {
    var l = new List<KeyValuePair<IntPtr,string>>();
    EnumWindows((h, p) => { if (IsWindowVisible(h)) { var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
      if (sb.Length > 0) l.Add(new KeyValuePair<IntPtr,string>(h, sb.ToString())); } return true; }, IntPtr.Zero);
    return l;
  }
  public static Bitmap Foto(IntPtr h) {
    RECT r; GetWindowRect(h, out r); int w = r.R - r.L, a = r.B - r.T;
    var bmp = new Bitmap(w, a);
    using (var g = Graphics.FromImage(bmp)) { var hdc = g.GetHdc(); PrintWindow(h, hdc, 2); g.ReleaseHdc(hdc); }
    return bmp;
  }
}
"@
$v = [Cap]::Ventanas()
if ($Listar) { $v | ForEach-Object { $_.Value }; return }
$m = $v | Where-Object { $_.Value -like "*$Titulo*" } | Select-Object -First 1
if (-not $m) { Write-Output "NO_ENCONTRADA: $Titulo"; return }
$bmp = [Cap]::Foto($m.Key)
New-Item -ItemType Directory -Force -Path (Split-Path $Salida) | Out-Null
$bmp.Save($Salida, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "OK $($m.Value) -> $Salida ($($bmp.Width)x$($bmp.Height))"
