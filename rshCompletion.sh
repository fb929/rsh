_rsh_completion_hosts(){
    COMPREPLY=( $(compgen -W "$(rshCompgen.py hosts)" -- "$2") )
}
_rsh_completion_groups(){
    COMPREPLY=( $(compgen -W "$(rshCompgen.py groups)" -- "$2") )
}
complete -F _rsh_completion_hosts sr
complete -F _rsh_completion_groups sExec
complete -F _rsh_completion_groups pExec
