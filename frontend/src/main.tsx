import React from 'react';
import { createRoot } from 'react-dom/client';
import './main.css';

function App() { return <main><p className="eyebrow">SHOWRUNNER / FOUNDATION</p><h1>Build a channel that never runs out of stories.</h1><p>Choose a channel preset, then let the agent pipeline turn an idea into a publish-ready Short—with a human in control.</p><section><strong>Channel presets</strong><div className="cards"><button>Last Signal<span>Survival-story thriller</span></button><button>The Quiet Discipline<span>Stoic philosophy</span></button></div></section></main>; }
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
