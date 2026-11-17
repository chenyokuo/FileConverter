import {createRoot} from 'react-dom/client';
import {VideoEditor} from '../src/components/VideoEditor';
import '@fontsource/inter/latin-400.css';import '@fontsource/noto-sans-tc/400.css';import '../src/styles.css';
import {defaults} from '../src/defaults';
createRoot(document.getElementById('root')!).render(<div className="app theme-dark" style={{padding:20,overflow:'auto','--accent':defaults.appearance.accent,'--accent-rgb':defaults.appearance.accent.slice(1).match(/../g)!.map(v=>parseInt(v,16)).join(' ')} as React.CSSProperties}><h1>影片編輯器</h1><VideoEditor hardware={[{id:'cpu',label:'CPU',available:true,encoder:'libx264',reason:''}]} notify={()=>{}}/></div>);
