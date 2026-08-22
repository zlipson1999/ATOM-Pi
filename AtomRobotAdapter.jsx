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

// Sized to the real device, not to a desktop browser. The Electron window is
// 480x800 fullscreen (chat-gui/src/main/index.js), and Home.jsx spends that
// height on a 28px status bar, a title block, and a 2x2 menu grid whose
// buttons are min-h-[100px] — leaving ~408px for the robot. AtomRobot renders
// height at size * 1.26, so anything above ~320 squeezes the menu below its
// minimum and the bottom row falls off the screen. Measured at 480x800:
// 340 -> menu gets 176px (needs 212), 442 -> 47px. 300 -> 226px, correct.
// Ratios follow upstream Avatar's sm/lg/xl relationship.
const SIZE = { sm: 92, lg: 230, xl: 300 };

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
  const px = size ?? (SIZE[variant] ?? SIZE.lg);
  return <AtomRobot state={state} size={px} className={className} onClick={onClick} />;
}
