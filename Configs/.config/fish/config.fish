set -g fish_greeting

if status is-interactive
    starship init fish | source
end

# List Directory
alias l='eza -lh --hyperlink  --icons=auto' # long list
alias ls='eza -1 --hyperlink   --icons=auto' # short list
alias ll='eza -lha --hyperlink --icons=auto --sort=name --group-directories-first' # long list all
alias ld='eza -lhD --hyperlink --icons=auto' # long list dirs
alias lt='eza --hyperlink --icons=auto --tree' # list folder as tree

# Handy change dir shortcuts
abbr .. 'cd ..'
abbr ... 'cd ../..'
abbr .3 'cd ../../..'
abbr .4 'cd ../../../..'
abbr .5 'cd ../../../../..'

# Always mkdir a path (this doesn't inhibit functionality to make a single dir)
abbr mkdir 'mkdir -p'
