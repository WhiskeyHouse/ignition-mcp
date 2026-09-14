import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
const cards = [{"title": "Connect a client", "description": "Run the server locally and start with a gateway information request.", "path": "quickstart"}, {"title": "Configure access", "description": "Set the gateway address, authentication, transport, and optional endpoints.", "path": "configuration"}, {"title": "Add runtime data", "description": "Configure the WebDev resources required for tags, alarms, and history.", "path": "webdev-setup"}];
export default function Home(): React.JSX.Element {
 return <Layout title="ignition-mcp" description="An MCP server for Ignition 8.3+ gateway operations, with optional WebDev endpoints for runtime data.">
  <main><section className="launch-hero"><p className="launch-label">IGNITION / DEVELOPER TOOLS</p><h1>Connect your assistant to Ignition.</h1><p className="lead">An MCP server for Ignition 8.3+ gateway operations, with optional WebDev endpoints for runtime data.</p>
  <div className="launch-actions"><Link className="button button--primary button--lg" to="/docs/installation">Get started</Link><Link className="button button--outline button--primary button--lg" to="/docs/quickstart">Try a first workflow</Link></div></section>
  <section className="launch-grid" aria-label="Documentation paths">{cards.map(card => <article key={card.path}><h2>{card.title}</h2><p>{card.description}</p><Link to={'/docs/' + card.path}>Read the guide →</Link></article>)}</section>
  <aside className="launch-maintainer"><p>I’m Patrick Mannion. I work on Ignition development tools and write about the work on FIELDNOTES.</p><p><a href="https://awake-iris-z6ww.here.now/about/">About me</a> · <a href="https://www.linkedin.com/in/mannionpatrick/">LinkedIn</a> · <a href="https://x.com/__pattym__">X</a> · <a href="https://github.com/WhiskeyHouse/ignition-mcp/graphs/contributors">Project contributors</a></p></aside></main>
 </Layout>;
}
