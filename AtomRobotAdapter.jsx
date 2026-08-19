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
 */
import AtomRobot from "./AtomRobot";
const PRIORITY=["error","boot","speaking","thinking","seeing","knowledge_search","web_search","tool_use","listening","idle","offline"];
export default function AtomRobotAdapter({ expression="idle", size=340 }) {
  const state = PRIORITY.includes(expression) ? expression : "idle";
  return <AtomRobot state={state} size={size} />;
}
