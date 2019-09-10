######## Helper functions ########

function make_clean()
{
    # Move previous files to "old" directory
    mv "${MINI_C}" "${MINI_EXE}" old
}

function generate_mini_c()
{
    cython -3 --embed "${MINI_PY}"
}

######## Platform-agnostic definitions ########

PROJECT_DIR=${HOME}/projects/miniquery
SCRIPT_DIR=${PROJECT_DIR}/scripts
MINI_PY=${SCRIPT_DIR}/mini.py
MINI_C=${SCRIPT_DIR}/mini.c

######## Main code ########

case $OSTYPE in
  *android*)

    MINI_EXE=${SCRIPT_DIR}/mini

    make_clean
    generate_mini_c

    # Generate EXE from C source file
    arm-linux-androideabi-clang -I /data/data/com.termux/files/usr/include/python3.7m -L /data/data/com.termux/files/usr/lib -o "${MINI_EXE}" "${MINI_C}" -lpython3.7m

    strip "${MINI_EXE}"
    ;;

  *linux*)

    MINI_EXE=${SCRIPT_DIR}/mini

    make_clean
    generate_mini_c

    gcc -I /usr/include/python3.4m -L /usr/lib64 -o "${MINI_EXE}" "${MINI_C}" -lpython3.4m

    strip "${MINI_EXE}"
    ;;

  *win*)
    echo "Windows not implemented."
    MINI_EXE=${SCRIPT_DIR}/mini.exe
    ;;
esac
