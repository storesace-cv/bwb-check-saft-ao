#!/usr/bin/env bash
# update_from_main.sh — Mantém o branch ATUAL sempre igual ao 'main' REMOTO.
# Uso: ./update_from_main.sh
# Variáveis opcionais:
#   REMOTE_NAME=origin (default)
#   MAIN_BRANCH=main   (default)
#   IGNORE_GITIGNORE=1 -> também limpa ficheiros ignorados (git clean -ffdx)
#   DRY_RUN=1          -> mostra o que faria, sem executar
#
# Segurança:
#  - Recusa executar no próprio MAIN (para evitar "auto-aniquilação" por engano)
#  - Aborta rebase/merge cherry-pick aplicados (ou pede para resolver)
#  - Usa --force-with-lease no push
#
set -euo pipefail

REMOTE_NAME="${REMOTE_NAME:-origin}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
DRY_RUN="${DRY_RUN:-0}"
CLEAN_FLAGS="-ffd"
if [[ "${IGNORE_GITIGNORE:-0}" == "1" ]]; then
  CLEAN_FLAGS="-ffdx"
fi

info() { printf "\033[1;34m[i]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ok]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[!]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[x]\033[0m %s\n" "$*"; }

# 0) Sanity checks
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { err "Não estás num repositório Git."; exit 1; }
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -z "${CURRENT_BRANCH}" || "${CURRENT_BRANCH}" == "HEAD" ]]; then
  err "HEAD destacado. Vai para um branch primeiro (ex.: git checkout my-saftpt)."
  exit 1
fi
if [[ "${CURRENT_BRANCH}" == "${MAIN_BRANCH}" ]]; then
  err "Estás em '${MAIN_BRANCH}'. Este script recusa executar no main — muda para o teu branch (ex.: my-saftpt)."
  exit 1
fi

# In-progress operations guard
for state in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD; do
  if [[ -e ".git/${state}" ]]; then
    err "Existe uma operação Git em curso (${state}). Conclui/aborta antes de continuar."
    exit 1
  fi
done

# 1) Garantir remoto e fetch
if ! git remote | grep -qx "${REMOTE_NAME}"; then
  err "Remote '${REMOTE_NAME}' não encontrado. Configura-o primeiro (git remote add ${REMOTE_NAME} <url>)."
  exit 1
fi
info "A obter estado de ${REMOTE_NAME}…"
git fetch --prune --tags "${REMOTE_NAME}"

# 2) Confirmar existência de ${REMOTE_NAME}/${MAIN_BRANCH}
if ! git show-ref --verify --quiet "refs/remotes/${REMOTE_NAME}/${MAIN_BRANCH}"; then
  err "Não encontrei ${REMOTE_NAME}/${MAIN_BRANCH}. Verifica o nome do branch remoto principal."
  exit 1
fi

info "Branch atual: ${CURRENT_BRANCH} → ficará 100% igual a ${REMOTE_NAME}/${MAIN_BRANCH}"
if [[ "${DRY_RUN}" == "1" ]]; then
  warn "DRY_RUN=1 → apenas a simular."
  echo "git reset --hard ${REMOTE_NAME}/${MAIN_BRANCH}"
  echo "git clean ${CLEAN_FLAGS}"
  echo "git push --force-with-lease ${REMOTE_NAME} HEAD:${CURRENT_BRANCH}"
  exit 0
fi

# 3) Reset + clean
info "A resetar (hard) para ${REMOTE_NAME}/${MAIN_BRANCH}…"
git reset --hard "${REMOTE_NAME}/${MAIN_BRANCH}"
info "A limpar ficheiros não versionados (git clean ${CLEAN_FLAGS})…"
git clean ${CLEAN_FLAGS}

# 4) Push forçado do branch atual
info "A alinhar o remoto (${CURRENT_BRANCH}) com ${REMOTE_NAME}/${MAIN_BRANCH}…"
git push --force-with-lease "${REMOTE_NAME}" "HEAD:${CURRENT_BRANCH}"

ok "O branch '${CURRENT_BRANCH}' (local e remoto) está agora exatamente igual a '${REMOTE_NAME}/${MAIN_BRANCH}'."
