import os
import sys
import subprocess
import string
import random

bashfile=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
bashfile='/tmp/'+bashfile+'.sh'

f = open(bashfile, 'w')
s = """#!/bin/bash

# Telegram Config
TOKEN=$(/usr/bin/env python -c "import os; print(os.environ.get('TOKEN'))")
if [[ "$(/usr/bin/env python -c "import os; print(os.environ.get('BUILDTYPE'))")" == "RELEASE" ]]; 
	then
		CHATID=$(/usr/bin/env python -c "import os; print(os.environ.get('CHATID'))")
		MESSAGEID=1198
elif [[ "$(/usr/bin/env python -c "import os; print(os.environ.get('BUILDTYPE'))")" == "TEST" ]]; 
	then
		CHATID=$(/usr/bin/env python -c "import os; print(os.environ.get('CHATIDTEST'))")
		MESSAGEID=0
else
		exit 0;
fi	
CHANGELOG=$(/usr/bin/env python -c "import os; print(os.environ.get('CHANGELOG'))")
BOT_MSG_URL="https://api.telegram.org/bot${TOKEN}/sendMessage"
BOT_BUILD_URL="https://api.telegram.org/bot${TOKEN}/sendDocument"
BOT_STICKER_URL="https://api.telegram.org/bot${TOKEN}/sendSticker"

# Build Machine details
cores=$(nproc --all)
os=$(cat /etc/issue)
time=$(TZ="Asia/Kolkata" date "+%a %b %d %r")

# send msgs to tg
tg_post_msg() {
  curl -s -X POST "$BOT_MSG_URL" -d chat_id="$CHATID" -d message_thread_id="$MESSAGEID" -d "disable_web_page_preview=true" -d "parse_mode=html" -d text="$1"
}


# send build to tg
tg_post_build()
{
	#Post MD5Checksum alongwith for easeness
	MD5CHECK=$(md5sum "$1" | cut -d' ' -f1)

	#Show the Checksum alongwith caption
	curl --progress-bar -F document=@"$1" "$BOT_BUILD_URL" -F message_thread_id="$MESSAGEID" -F chat_id="$CHATID" -F "disable_web_page_preview=true" -F "parse_mode=Markdown" -F caption="$2 | *MD5 Checksum : *\\`$MD5CHECK\\`"
}

# send a nice sticker ro act as a sperator between builds
tg_post_sticker() {
  curl -s -X POST "$BOT_STICKER_URL" -d chat_id="$CHATID" -d message_thread_id="$MESSAGEID" -d sticker="CAACAgUAAxkBAAEKCfxk3IWJbpyf9AJVzCr7WqNariv-YgACfwoAAiV14VZRQDfFXOn16DAE"
}

kernel_dir="${PWD}"
objdir="${kernel_dir}/out"
kf="$kernel_dir/packaging"
builddir="${kernel_dir}/build"
avbtool=${kernel_dir}/scripts/avb/avbtool.py
ZIMAGE=$kernel_dir/out/arch/arm64/boot/Image.gz-dtb
DTBOIMAGE=$kernel_dir/out/arch/arm64/boot/dtbo.img
version="v3.0"
build_date="$(date +"%d-%m-%Y")"
kernel_version=4.19.325
ksu_next_apk_name=KernelSU_Next_v1.0.5_12430-release.apk
ksu_next_apk=https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v1.0.5/KernelSU_Next_v1.0.5_12430-release.apk
kernel_name="NeverSettle-Kernel-$version-avicii"
zip_name="$kernel_name-$(date +"%d%m%Y-%H%M").zip"
TC_DIR=$HOME/tc/
export ARCH=arm64
export SUBARCH=arm64
export CONFIG_FILE="avicii_defconfig debugfs.config"
export BRAND_SHOW_FLAG=oneplus
export CCACHE=$(command -v ccache)
export PATH="${PWD}/clang-llvm/bin:${PATH}"
export CC="ccache clang"
export CLANG_TRIPLE="aarch64-linux-gnu-"
export CROSS_COMPILE="aarch64-linux-gnu-"
export CROSS_COMPILE_ARM32="arm-linux-gnueabi-"
export LLVM=1
export LLVM_IAS=1
export DTC_EXT=/bin/dtc

#start off by sending a trigger msg
tg_post_sticker
tg_post_msg "<b>NeverSettle Kernel Build Triggered ⌛</b>%0A<b>============================</b>%0A<b>Kernel : </b><code>$kernel_name</code>%0A<b>Machine : </b><code>$os</code>%0A<b>Cores : </b><code>$cores</code>%0A<b>Time : </b><code>$time</code>"

# Colors
NC='\\033[0m'
RED='\\033[0;31m'
LRD='\\033[1;31m'
LGR='\\033[1;32m'

make_defconfig()
{
    START=$(date +"%s")
    echo -e ${LGR} "########### Generating Defconfig ############${NC}"
    make -s ARCH=arm64 O=out $CONFIG_FILE -j$(nproc --all)
}
compile()
{
    echo -e ${LGR} "######### Compiling kernel #########${NC}"
    make ARCH=arm64 O=out -j$(nproc --all) \\
    2>&1 | tee error.log
    python3 ${avbtool} add_hash_footer --image ${DTBOIMAGE} --partition_size 25165824 --partition_name dtbo
}

completion() {
  cd ${objdir}
  COMPILED_IMAGE=arch/arm64/boot/Image.gz-dtb
  COMPILED_DTBO=arch/arm64/boot/dtbo.img
  if [[ -f ${COMPILED_IMAGE} && ${COMPILED_DTBO} ]]; then

    mv -f $ZIMAGE ${COMPILED_DTBO} $kf

    cd $kf
    find . -name "*.zip" -type f
    find . -name "*.zip" -type f -delete
    sed -i "s/version.string=/version.string=$version/g" anykernel.sh
    sed -i "s/date.string=/date.string=$build_date/g" anykernel.sh
    sed -i "s/Based on Linux Kernel KERNEL_VERSION_STRING/Based on Linux Kernel $kernel_version/g" META-INF/com/google/android/update-binary
    zip -r $zip_name *
    mv $kf/$zip_name $HOME/$zip_name
    curl -sL ${ksu_apk} > $HOME/${ksu_next_apk_name}
    END=$(date +"%s")
    DIFF=$(($END - $START))
    BUILDTIME=$(echo $((${END} - ${START})) | awk '{print int ($1/3600)" Hours:"int(($1/60)%60)"Minutes:"int($1%60)" Seconds"}')
    tg_post_build "$HOME/$zip_name" "Build took : $((DIFF / 60)) minute(s) and $((DIFF % 60)) second(s)"
    tg_post_msg "<b>Changelog ($(date +%d-%m-%Y))</b>%0A<code>$CHANGELOG</code>"
    tg_post_build "$HOME/${ksu_next_apk_name}" "KernelSU-Next Manager for this build"
    tg_post_msg "<code>Compiled successfully✅</code>"
    tg_post_msg "<b>Support the developer❤️</b>%0A<b>UPI:</b> <code>sreeshankark@axl</code>%0A<b>Paypal:</b> PayPal.me/SreeshankarK"
    curl --upload-file $HOME/$zip_name https://free.keep.sh
    echo
    echo -e ${LGR} "############################################"
    echo -e ${LGR} "######### Compilation suceeded :) ##########"
    echo -e ${LGR} "############################################${NC}"
  else
    tg_post_build "$kernel_dir/error.log" "$CHATID" "Debug Mode Logs"
    tg_post_msg "<code>Compilation failed❎</code>"
    echo -e ${RED} "############################################"
    echo -e ${RED} "##         Compilation failed :(          ##"
    echo -e ${RED} "############################################${NC}"
  fi
}
make_defconfig
if [ $? -eq 0 ]; then
  tg_post_msg "<code>Defconfig generated successfully✅</code>"
fi
compile
completion
cd ${kernel_dir}
"""
f.write(s)
f.close()
os.chmod(bashfile, 0o755)
bashcmd=bashfile
for arg in sys.argv[1:]:
  bashcmd += ' '+arg
subprocess.call(bashcmd, shell=True)
