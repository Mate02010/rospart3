# Funciones para los guiones de terminal: muestran el comando como si se escribiera y luego lo corren.
mostrar() {
  printf '\033[1;32mbrayan@ros2\033[0m:\033[1;34m~/proyecto_final_ws\033[0m$ '
  local t="$*"
  for ((i=0; i<${#t}; i++)); do printf '%s' "${t:$i:1}"; sleep 0.02; done
  echo
  eval "$@"
}
nota() { printf '\033[1;33m# %s\033[0m\n' "$*"; }
esperar_topico() { for i in $(seq 1 60); do timeout 10 ros2 topic echo "$1" --once >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
esperar_nav2() { for i in $(seq 1 100); do grep -aq "lifecycle_manager_navigation.*Managed nodes are active" "$1" && return 0; sleep 3; done; return 1; }
esperar_activo() { for i in $(seq 1 60); do grep -aq "Managed nodes are active" "$1" && return 0; sleep 3; done; return 1; }
