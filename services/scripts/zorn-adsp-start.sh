#!/bin/bash
# Bring up the ADSP from userspace. The probe-time auto-boot always fails (-ENOENT)
# because remoteproc probes during kernel init, before any rootfs is mounted.
# The ADSP charger firmware is what sources VBUS on the Type-C port, so without
# this the USB host port stays unpowered and no keyboard works.
set -u
S=/sys/class/remoteproc/remoteproc0/state

[ -e "$S" ] || { echo "zorn-adsp: $S missing"; exit 0; }

name=$(cat /sys/class/remoteproc/remoteproc0/name 2>/dev/null)
echo "zorn-adsp: remoteproc0 name=$name state=$(cat $S 2>/dev/null)"

if [ ! -f /lib/firmware/qcom/sm8650/adsp.mbn ]; then
  echo "zorn-adsp: /lib/firmware/qcom/sm8650/adsp.mbn missing, cannot start"
  exit 0
fi

for try in 1 2 3; do
  st=$(cat "$S" 2>/dev/null)
  if [ "$st" = running ]; then
    echo "zorn-adsp: already running"
    break
  fi
  if echo start > "$S" 2>/tmp/zorn-adsp.err; then
    echo "zorn-adsp: attempt $try accepted"
  else
    echo "zorn-adsp: attempt $try failed: $(cat /tmp/zorn-adsp.err 2>/dev/null)"
  fi
  sleep 4
  st=$(cat "$S" 2>/dev/null)
  echo "zorn-adsp: attempt $try -> state=$st"
  [ "$st" = running ] && break
done

echo "zorn-adsp: final state=$(cat "$S" 2>/dev/null)"
