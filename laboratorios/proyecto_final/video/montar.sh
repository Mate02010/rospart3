#!/bin/bash
# Arma el video final: tarjetas de título + clips (algunos acelerados). Uso: montar.sh
set -e
V="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video"
T="$V/textos"; W=~/videos/montaje; mkdir -p $W; rm -f $W/*.mp4
FB=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
FR=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
FPS=24
ENC="-c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -r $FPS"

tarjeta() {  # tarjeta <salida> <segundos> <archivo_titulo> <archivo_sub> [archivo_extra]
  local extra=""
  [ -n "$5" ] && extra=",drawtext=fontfile=$FR:textfile='$5':fontcolor=0xb8c4cc:fontsize=30:x=(w-text_w)/2:y=h/2+120"
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x14181c:s=1920x1080:d=$2:r=$FPS" -vf \
"drawtext=fontfile=$FB:textfile='$3':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=h/2-110,\
drawbox=x=(iw-520)/2:y=ih/2-20:w=520:h=4:color=0xeb6834:t=fill,\
drawtext=fontfile=$FR:textfile='$4':fontcolor=0xdde3e8:fontsize=34:x=(w-text_w)/2:y=h/2+30$extra,\
fade=t=in:st=0:d=0.4,fade=t=out:st=$(awk "BEGIN{print $2-0.4}"):d=0.4" $ENC $W/$1.mp4
}

clip() {  # clip <nombre> <factor_velocidad> <etiqueta>
  local f=$2 lbl=""
  [ "$f" != "1" ] && lbl=",drawtext=fontfile=$FB:text='x$f':fontcolor=white:fontsize=30:box=1:boxcolor=0xeb6834@0.9:boxborderw=10:x=w-text_w-30:y=20"
  ffmpeg -loglevel error -y -i ~/videos/$1.mp4 -vf \
"setpts=PTS/$f,fps=$FPS,drawtext=fontfile=$FB:textfile='$3':fontcolor=white:fontsize=24:box=1:boxcolor=0x14181c@0.85:boxborderw=10:x=20:y=60$lbl" \
    -an $ENC $W/$1_clip.mp4
}

tarjeta 00_intro 6 "$T/intro_1.txt" "$T/intro_2.txt" "$T/intro_3.txt"
tarjeta 00b_autores 3 "$T/autores.txt" "$T/intro_3.txt"
for p in p1 p2 p3 p4 p5 final; do
  tarjeta ${p}_tarjeta 4 "$T/${p}_1.txt" "$T/${p}_2.txt"
done
clip p1 1 "$T/p1_1.txt"
clip p2 2 "$T/p2_1.txt"
clip p3 4 "$T/p3_1.txt"
clip p4 1.5 "$T/p4_1.txt"
clip p5 2 "$T/p5_1.txt"
clip final 2 "$T/final_1.txt"
tarjeta 99_cierre 5 "$T/cierre_1.txt" "$T/cierre_2.txt"

: > $W/lista.txt
for s in 00_intro 00b_autores p1_tarjeta p1_clip p2_tarjeta p2_clip p3_tarjeta p3_clip p4_tarjeta p4_clip p5_tarjeta p5_clip final_tarjeta final_clip 99_cierre; do
  echo "file '$W/$s.mp4'" >> $W/lista.txt
done
ffmpeg -loglevel error -y -f concat -safe 0 -i $W/lista.txt -f lavfi -i anullsrc=r=44100:cl=stereo \
  -c:v copy -c:a aac -shortest -movflags +faststart ~/videos/video_proyecto_final.mp4
cp ~/videos/video_proyecto_final.mp4 "$V/Video_Proyecto_Final_Robotica.mp4"
echo "Duración: $(ffprobe -v error -show_entries format=duration -of csv=p=0 ~/videos/video_proyecto_final.mp4) s"
ls -la "$V/Video_Proyecto_Final_Robotica.mp4"
