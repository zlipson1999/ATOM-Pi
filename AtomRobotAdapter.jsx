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
// 480x800 fullscreen (chat-gui/src/main/index.js). On the ATOM hub that
// height is spent on a 28px status bar (+4px border), 16px padding top and
// bottom, the title block, a 48px gap, a 2x2 menu grid whose buttons are
// min-h-[100px] (212px with its gap), and the 56px DESKTOP bar with its 12px
// margin — about 460px before the robot gets any. AtomRobot renders height at
// size * 1.26, so the robot must stay under ~269 or the bottom row falls off
// the screen. Measured by rendering the real layout at 480x800:
//   442 (an earlier variant mapping) -> menu 47px, two tiles off-screen
//   340 (an earlier default)         -> menu 176px, still short of 212
//   260                              -> everything fits with room to spare
// Ratios follow upstream Avatar's sm/lg/xl relationship.
const SIZE = { sm: 84, lg: 200, xl: 260 };

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
