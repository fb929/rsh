_rsh_completion(){
    COMPREPLY=( $(compgen -W "$(./rshCompgen.py)" -- "$2") )
}
complete -F _rsh_completion ./sr
