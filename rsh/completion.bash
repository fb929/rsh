# bash completion for rsh tools; install with:  eval "$(rshCompgen completion)"
_rsh_completion_hosts(){
    COMPREPLY=( $(compgen -W "$(rshCompgen hosts)" -- "$2") )
}
_rsh_completion_groups(){
    COMPREPLY=( $(compgen -W "$(rshCompgen groups)" -- "$2") )
}
complete -F _rsh_completion_hosts sr
complete -F _rsh_completion_groups sExec
complete -F _rsh_completion_groups pExec
