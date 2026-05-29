#!/usr/bin/env bash
# Audio/visual notification for opencode task events.
# Usage: ./scripts/notify.sh <type> [message]
#   type: done | question | error | warning | info

TYPE="${1:-info}"
MSG="${2:-}"

notify_via_sound() {
  local sound
  case "$TYPE" in
    done)     sound="complete" ;;
    question) sound="question" ;;
    error)    sound="error" ;;
    warning)  sound="warning" ;;
    info)     sound="info" ;;
  esac
  # Try aplay with bundled sounds, fallback to terminal bell
  if command -v aplay &>/dev/null; then
    local sound_dir="${HOME}/.config/opencode/sounds"
    local wav="${sound_dir}/${sound}.wav"
    if [ -f "$wav" ]; then
      aplay -q "$wav" &
    else
      # Simple beep sequences as morse-like patterns
      case "$TYPE" in
        done)     echo -ne "\a\a" ;;
        question) echo -ne "\a" ;;
        error)    echo -ne "\a\a\a" ;;
        warning)  echo -ne "\a\a" ;;
        info)     echo -ne "\a" ;;
      esac
    fi
  fi
}

notify_via_desktop() {
  if command -v notify-send &>/dev/null; then
    local urgency="normal"
    [ "$TYPE" = "error" ] && urgency="critical"
    [ "$TYPE" = "warning" ] && urgency="critical"
    notify-send -u "$urgency" "opencode [$TYPE]" "${MSG:-Task $TYPE}" 2>/dev/null &
  fi
}

notify_via_terminal() {
  case "$TYPE" in
    done)     printf "\033[32m✔\033[0m %s\n" "${MSG:-Done}" ;;
    question) printf "\033[33m?\033[0m %s\n" "${MSG:-Question}" ;;
    error)    printf "\033[31m✘\033[0m %s\n" "${MSG:-Error}" ;;
    warning)  printf "\033[33m⚠\033[0m %s\n" "${MSG:-Warning}" ;;
    info)     printf "\033[36mi\033[0m %s\n" "${MSG:-Info}" ;;
  esac
}

notify_via_sound
notify_via_desktop
notify_via_terminal
