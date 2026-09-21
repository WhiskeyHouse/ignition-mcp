(() => {
  const demos = {"pi": {"title": "Ignition MCP + Agent"}};
  const name = new URLSearchParams(location.search).get('demo');
  const demo = Object.hasOwn(demos, name) ? demos[name] : null;
  if (!demo) { document.querySelector('#player').textContent = 'Recording not found.'; return; }
  document.title = demo.title;
  const mount = document.querySelector('#player');
  const player = AsciinemaPlayer.create(name + '.cast', mount, {
    cols:92, rows:26, controls:true, fit:'width', preload:true,
    autoplay:false, poster:'npt:0:03', speed:1.2,
    idleTimeLimit:name === 'nvim' ? 4 : 2, cursorMode:'steady'
  });
  // Documentation demos are reader-controlled; opening a guide never starts playback.
  const observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) player.pause();
  });
  observer.observe(mount);
  document.addEventListener('visibilitychange', () => { if (document.hidden) player.pause(); });
  window.addEventListener('pagehide', event => { if (!event.persisted) player.dispose(); });
})();
