/**
 * Drop-in replacement for pocket-ai's Avatar. Same prop surface;
 * renders the full ATOM robot and applies the ONE state-priority
 * rule so the body can never contradict itself:
 *   error > boot > speaking > thinking > seeing > knowledge_search
 *   > web_search > tool_use
 *         > listening > idle   (offline when the backend is gone)
 * The GUI feeds expression={voiceStatus} from real backend
 * voice_status events (which now include seeing/tool_use — verified
 * patch), so precedence collapses to trusting the single freshest
 * backend-reported state, with unknown strings degraded to idle.
 *
 * Home.jsx renders this as:
 *   <Avatar variant="xl" animate={true} expression={voiceStatus}
 *           className="cursor-pointer transition-all ... scale-110 ..." />
 * so variant and className are accepted and forwarded rather than
 * dropped — dropping them rendered the robot at the wrong size and
 * lost the "recording" scale cue. `animate` is accepted and ignored:
 * AtomRobot already honours prefers-reduced-motion itself.
 * Push-to-talk is unaffected either way — Home.jsx puts those mouse
 * handlers on the wrapping div, not on this component.
 */
import AtomRobot from "./AtomRobot";

const PRIORITY = ["error", "boot", "speaking", "thinking", "seeing",
                  "knowledge_search", "web_search", "tool_use",
                  "listening", "idle", "offline"];

// Mirrors upstream Avatar's scale factors (sm 0.4 / lg 1 / xl 1.3).
const SCALE = { sm: 0.4, lg: 1, xl: 1.3 };
const BASE = 340;

export default function AtomRobotAdapter({
  expression = "idle",
  variant = "lg",
  className = "",
  size,
  // eslint-disable-next-line no-unused-vars
  animate = true,
  onClick,
}) {
  const state = PRIORITY.includes(expression) ? expression : "idle";
  const px = size ?? Math.round(BASE * (SCALE[variant] ?? 1));
  return <AtomRobot state={state} size={px} className={className} onClick={onClick} />;
}
