if [[ $0 =~ buildUtils ]]; then
    echo Not an executable script.
    exit 1
fi

######## Helper functions ########

function make_clean() {
    # Move previous files to "old" directory
    echo Backing up older generated files ...
    mkdir -p "${BUILD_DIR}"
    for filename in "${CYTHON_CFG_FILE}"  "${GENERATED_CFILE}"  "${OBJECT_FILE}"  "${SHARED_LIBRARY}"; do
        mv "$filename" "${BUILD_DIR}"/old    # To suppress feedback: 2>/dev/null
    done
}

function generate_cython_config() {
    echo Generating cython cfg file ${CYTHON_CFG_FILE} ...
    for fn in "${SRC_DIR}"/*.py; do
      bn=`basename "$fn"`
      if [[ ! "$bn" =~ ^(setup|include)\.py$ ]]; then
        echo include \""$bn"\" >> "${CYTHON_CFG_FILE}"
      fi
    done
}

function generate_c_file() {
    echo Generating C file $GENERATED_CFILE ...
    "$CYTHON" -3 "${CYTHON_CFG_FILE}" -o "${GENERATED_CFILE}"
    [[ $? == 0 ]] || return $?
    ls -l "$GENERATED_CFILE"
}


