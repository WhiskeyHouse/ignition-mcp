import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
const cards = [{"title": "Connect a client", "description": "Run the server locally, then list tools and read the gateway from your assistant.", "path": "quickstart"}, {"title": "Configure", "description": "The four settings, and how ign resolves the gateway credential.", "path": "configuration"}, {"title": "Tool reference", "description": "Composite tools, ign:// resources, prompts, and the proxied ign catalog.", "path": "reference"}];
export default function Home(): React.JSX.Element {
 const demosUrl = useBaseUrl('/demos/index.html');
 return <Layout title="ignition-mcp" description="A local HTTP front for `ign mcp serve`: every ign tool, plus composite workflows, resources, and prompts.">
  <main><section className="launch-hero"><p className="launch-label">IGNITION / DEVELOPER TOOLS</p><h1>Connect your assistant to Ignition.</h1><p className="lead">A local HTTP front for <code>ign mcp serve</code>: every ign tool, plus composite workflows, resources, and prompts.</p>
  <div className="launch-actions"><Link className="button button--primary button--lg" to="/docs/installation">Get started</Link><Link className="button button--outline button--primary button--lg" to="/docs/quickstart">Try a first workflow</Link></div></section>
  <section className="launch-grid" aria-label="Documentation paths">{cards.map(card => <article key={card.path}><h2>{card.title}</h2><p>{card.description}</p><Link to={'/docs/' + card.path}>Read the guide →</Link></article>)}</section>
  <section className="launch-demos" id="demos" aria-label="Recorded walkthroughs"><h2>See it in use</h2><p>Recorded sessions against a fictional batch process. Press play to explore.</p>
    <h3>Ignition MCP + Agent</h3><div className="terminal-demo"><iframe className="terminal-demo-frame" src={demosUrl + "?demo=pi"} title="Ignition MCP + Agent terminal walkthrough" loading="lazy" allowFullScreen /></div><p>An agent checks gateway health, discovers tags, reads batch conditions and traceability IDs, then discusses hold readiness and questions for the operator.</p>
    <Link to="/docs/demos">Walkthrough details and recording downloads →</Link></section>
  <aside className="launch-maintainer"><p>I’m Patrick Mannion. I work on Ignition development tools and write about the work on FIELDNOTES.</p><p><a href="https://awake-iris-z6ww.here.now/about/">About me</a> · <a href="https://www.linkedin.com/in/mannionpatrick/">LinkedIn</a> · <a href="https://x.com/__pattym__">X</a> · <a href="https://github.com/WhiskeyHouse/ignition-mcp/graphs/contributors">Project contributors</a></p></aside></main>
 </Layout>;
}
