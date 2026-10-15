(() => {
  const $ = (id) => document.getElementById(id);
  if (!$("restauration")) return;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const groups = {
    interface: "Interface",
    interactions: "Interactions",
    footsteps: "Pas & déplacements",
    ambient: "Ambiances",
    tuto: "Voix du tutoriel",
  };
  const state = {
    id: "cra-1",
    gender: 1,
    group: "classes",
    pose: "default",
    facet: "illustration",
    stadium: 0,
    musicKind: "all",
  };
  const audio = $("restoration-audio");
  audio.volume = 0.35;
  let inventory,
    activeTrack = null,
    audioContext,
    analyser,
    waveFrame;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const labels = {
    default: "Vestiaire",
    winner: "Victoire",
    versus: "Face-à-face",
  };
  const metric = (found, total, label, note) => {
    const box = el("div", null, "restoration-metric");
    box.append(el("strong", `${found} / ${total}`), el("span", label));
    const bar = el("progress");
    bar.max = total || 1;
    bar.value = found;
    bar.setAttribute("aria-label", `${label} : ${found} sur ${total}`);
    box.append(bar, el("small", note));
    return box;
  };
  const selected = () =>
    inventory.characters.find((c) => c.id === state.id) ||
    inventory.characters[0];
  function choices() {
    return inventory.characters.filter(
      (c) =>
        (state.group === "heroes"
          ? !!c.hero
          : !c.hero && c.gender === state.gender) &&
        (!$("character-found-only").checked || c.body_available),
    );
  }
  function chooseCharacter(id) {
    state.id = id;
    const c = selected();
    if (!c.poses[state.pose]) state.pose = "default";
    renderCharacter();
    renderPicker();
  }
  function renderPicker() {
    const list = choices(),
      grid = $("character-class-grid");
    grid.replaceChildren();
    for (const c of list) {
      const b = el("button");
      b.type = "button";
      b.setAttribute(
        "aria-label",
        `${c.name}, ${c.gender === 1 ? "homme" : "femme"} : corps ${c.body_available ? "retrouvé" : "à retrouver"}`,
      );
      b.setAttribute("aria-pressed", String(c.id === state.id));
      const image = el("img");
      image.src = c.hero ? c.poses.default || c.icon : c.icon;
      image.alt = "";
      image.width = 80;
      image.height = 96;
      image.loading = "lazy";
      b.append(
        image,
        el("span", null, "character-dot" + (c.body_available ? " found" : "")),
      );
      b.onclick = () => chooseCharacter(c.id);
      grid.append(b);
    }
    if (!list.length)
      grid.append(
        el(
          "p",
          "Aucun corps d’origine retrouvé pour ce filtre. Les illustrations restent consultables en décochant la case.",
          "empty-picker",
        ),
      );
    $("character-picker-count").textContent =
      `${list.length} ${state.group === "heroes" ? "légende(s)" : "variante(s)"} dans cette sélection.`;
    for (const button of document.querySelectorAll("[data-gender]")) {
      button.disabled = state.group === "heroes";
      button.setAttribute(
        "aria-pressed",
        String(Number(button.dataset.gender) === state.gender),
      );
    }
    $("pick-classes").setAttribute(
      "aria-pressed",
      String(state.group === "classes"),
    );
    $("pick-heroes").setAttribute(
      "aria-pressed",
      String(state.group === "heroes"),
    );
  }
  function renderCharacter() {
    const c = selected(),
      sex = c.gender === 1 ? "Homme" : "Femme",
      portrait = c.poses[state.pose] || c.poses.default;
    $("character-class-name").textContent = c.name;
    $("character-variant").textContent = c.hero
      ? `${c.class_name} · personnage spécial`
      : sex;
    if (portrait) {
      $("character-portrait").src = portrait;
      $("character-portrait").hidden = false;
    } else $("character-portrait").hidden = true;
    $("character-portrait").alt =
      `${c.name}, ${sex.toLowerCase()}, illustration originale : ${labels[state.pose]}`;
    $("portrait-credit").textContent = portrait
      ? "ILLUSTRATION ORIGINALE · CLIENT FLASH"
      : "ILLUSTRATION CONSERVÉE DANS LE CLIENT · APERÇU À CAPTURER";
    for (const b of document.querySelectorAll("[data-pose]")) {
      b.disabled = !c.poses[b.dataset.pose];
      b.setAttribute("aria-pressed", String(b.dataset.pose === state.pose));
    }
    $("character-log").textContent =
      `Dossier ${c.name} · ${sex.toLowerCase()}. ${c.body_available ? "Pièces animées d’origine retrouvées." : "Corps propre à retrouver ; remplacement Crâ dans le jeu."}`;
    $("character-body-state").textContent = c.body_available
      ? "Corps d’origine retrouvé"
      : "Corps propre à retrouver";
    document.querySelector(".facet-body").classList.toggle("is-missing", !c.body_available);
    $("character-body-note").textContent = c.body_available
      ? `Le fichier ${c.body_path.split("/").pop()} est présent. La fidélité des mouvements reste à tester.`
      : "Le jeu utilise un corps Crâ de secours. Avoir l’illustration ne signifie pas avoir les pièces du pantin animé.";
    const source = $("character-body-source");
    source.hidden = !c.body_available;
    if (c.body_available) source.href = c.body_path;
    $("character-dossier-note").textContent =
      `${Object.keys(c.poses).length} poses consultables. ${c.body_available ? "Corps retrouvé." : "Corps de remplacement."} Couleurs à comparer aux archives.`;
    for (const b of document.querySelectorAll("[data-facet]"))
      b.setAttribute("aria-pressed", String(b.dataset.facet === state.facet));
    const facet =
      state.facet === "body"
        ? [
            c.body_available
              ? "Pièces du corps : retrouvées"
              : "Pièces du corps : manquantes",
            c.body_available
              ? "Le jeu de pièces de ce personnage existe dans les fichiers récupérés. Il faut encore vérifier les animations en match."
              : "Nous recherchons les éléments du pantin Flash : tête, torse, bras, jambes, accessoires et leurs variantes.",
          ]
        : state.facet === "colors"
          ? [
              "Couleurs : à vérifier",
              "Les palettes permettent de jouer. Leur fidélité aux teintes d’origine des classes et des personnages doit encore être confirmée.",
            ]
          : [
              "Illustrations : retrouvées",
              `${Object.keys(c.poses).length} poses exportées ici depuis le client original. Les illustrations et les corps animés sont des ressources distinctes.`,
            ];
    $("character-facet-title").textContent = facet[0];
    $("character-facet-detail").textContent = facet[1];
    $("character-help").dataset.volunteer =
      `Restauration de ${c.name} (${sex.toLowerCase()}) — ${c.body_available ? "vérification des animations et des couleurs" : "recherche des pièces du corps animé et des couleurs"}`;
  }
  function resetCharacter() {
    state.id = "cra-1";
    state.group = "classes";
    state.gender = 1;
    state.pose = "default";
    state.facet = "illustration";
    $("character-found-only").checked = false;
    $("restoration-player-name").value = "Aria";
    renderPicker();
    renderCharacter();
  }
  function setGroup(group) {
    state.group = group;
    const list = choices();
    if (list.length) state.id = list[0].id;
    renderPicker();
    renderCharacter();
  }
  function dossier() {
    const c = selected(),
      box = $("character-dossier-content");
    box.replaceChildren();
    $("character-dossier-title").textContent =
      `${$("restoration-player-name").value.trim() || c.name} · dossier ${c.name}`;
    for (const [name, value] of [
      [
        "Illustrations",
        `${Object.keys(c.poses).length} poses consultables depuis les dessins originaux`,
      ],
      [
        "Corps animé",
        c.body_available
          ? "Jeu de pièces retrouvé"
          : "Corps Crâ de remplacement ; pièces propres manquantes",
      ],
      ["Couleurs", "Palettes jouables ; fidélité à confirmer"],
      [
        "Priorité",
        c.body_available
          ? "Comparer les mouvements et les couleurs avec des archives"
          : "Retrouver ou restaurer les pièces du pantin Flash",
      ],
    ]) {
      const row = el("p");
      row.append(el("strong", name + " : "), document.createTextNode(value));
      box.append(row);
    }
    if (c.body_available) {
      const link = el("a", "Télécharger le fichier de pièces (.swl) ↗");
      link.href = c.body_path;
      link.download = "";
      box.append(link);
    }
    $("character-dossier-dialog").showModal();
  }
  function audioName(track) {
    const name = track.file
      .split("/")
      .pop()
      .replace(/\.mp3$/, "");
    const special = {
      bouton_generique: "Bouton de l’interface",
      bouton_ok_fin_phase_tactique: "Validation des ordres",
      fleche_drop_02: "Déplacement d’une flèche",
      wrong: "Mauvaise réponse",
      reac_bouftous: "Réaction des Bouftous",
      reac_crabes: "Réaction des crabes",
    };
    if (special[name]) return special[name];
    return name
      .replace(/^music_resolution_loop_/, "Résolution · boucle ")
      .replace(/^music_tactic_loop_/, "Tactique · boucle ")
      .replace(/^tuto_loop_/, "Tutoriel · boucle ")
      .replace(/^shortpass_/, "Passe courte ")
      .replace(/^ko_front_run_/, "Chute en course ")
      .replace(/^cutscenes-illustration-/, "Cinématique · ")
      .replaceAll("_", " ");
  }
  function trackRow(track, role, large = false) {
    const row = el("div", null, "archive-track"),
      button = el("button", track.available ? "▷" : "—");
    button.type = "button";
    button.disabled = !track.available;
    button.dataset.audioFile = track.file;
    button.setAttribute(
      "aria-label",
      track.available
        ? `Écouter : ${audioName(track)}`
        : `Fichier manquant : ${audioName(track)}`,
    );
    button.setAttribute("aria-pressed", "false");
    button.onclick = () => playTrack(track, role);
    row.append(button);
    const copy = el("div"),
      title = el("div");
    title.append(
      el("strong", audioName(track)),
      el(
        "small",
        `${role || groups[track.category] || track.category} · ${track.file}`,
      ),
    );
    copy.append(title);
    if (large)
      copy.append(
        el(
          "span",
          track.available ? "Retrouvé" : "À retrouver",
          "asset-state" + (track.available ? "" : " missing"),
        ),
      );
    else
      title.append(
        el(
          "small",
          track.restored_low_quality
            ? "Restauré, qualité basse"
            : track.available ? "Fichier retrouvé" : "Fichier à retrouver",
        ),
      );
    row.append(copy);
    return row;
  }
  function renderStadium() {
    const s = inventory.stadiums[state.stadium];
    $("stadium-name").textContent = s.name;
    $("stadium-image").src = s.image;
    $("stadium-image").alt = `Fond tactique original du stade ${s.name}`;
    $("stadium-position").textContent =
      `${state.stadium + 1} / ${inventory.stadiums.length}`;
    $("stadium-zoom").value = 100;
    $("stadium-zoom-value").value = "100 %";
    $("stadium-image").style.transform = "scale(1)";
    for (const b of $("stadium-grid").querySelectorAll("button"))
      b.setAttribute(
        "aria-pressed",
        String(Number(b.dataset.index) === state.stadium),
      );
    const status = $("stadium-asset-status");
    status.replaceChildren();
    for (const [name, found] of [
      ["Fond tactique 2D", s.surface_available],
      ["Texture de la surface", s.surface_available],
      ["Décor et géométrie 3D d’origine", s.original_geometry_available],
    ]) {
      const line = el("div", null, "stadium-asset-line");
      line.append(
        el("span", name),
        el(
          "strong",
          found ? "Retrouvé" : "À retrouver",
          "asset-state" + (found ? "" : " missing"),
        ),
      );
      status.append(line);
    }
    $("stadium-honesty").textContent = s.original_geometry_available
      ? "Le modèle de Cania est retrouvé. Les textures, les animations et les détails restent à comparer à des archives du jeu."
      : "Le fond 2D et sa surface sont retrouvés. En 3D, le jeu réutilise encore la géométrie et les décors de Cania : le décor propre à ce stade reste à restaurer.";
    const unique = [...new Map(s.tracks.map((t) => [t.file, t])).values()];
    $("stadium-music-count").textContent =
      `${unique.filter((t) => t.available).length} / ${unique.length} pistes référencées retrouvées (musiques et ambiance).`;
    $("stadium-help").dataset.volunteer =
      `Archives du stade ${s.name} : décors 3D, textures, musiques et ambiance d’origine`;
    renderStadiumTracks();
  }
  function renderStadiumTracks() {
    const list = $("stadium-track-list");
    list.replaceChildren();
    const tracks = inventory.stadiums[state.stadium].tracks.filter(
      (t) => state.musicKind === "all" || t.role === state.musicKind,
    );
    tracks.forEach((t) => list.append(trackRow(t, t.role)));
    if (!tracks.length)
      list.append(
        el("p", "Aucune piste référencée pour ce filtre.", "workshop-small"),
      );
    for (const b of document.querySelectorAll("[data-music-kind]"))
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.musicKind === state.musicKind),
      );
    syncAudioButtons();
  }
  function changeStadium(index) {
    state.stadium =
      (index + inventory.stadiums.length) % inventory.stadiums.length;
    if (activeTrack?.stadium) audio.pause();
    renderStadium();
  }
  function renderSoundChart() {
    const chart = $("sound-category-chart");
    chart.replaceChildren();
    for (const [category, name] of Object.entries(groups)) {
      const files = inventory.audio.filter((a) => a.category === category),
        found = files.filter((a) => a.available).length;
      const b = el("button", null, "sound-category-button");
      b.type = "button";
      b.dataset.category = category;
      b.setAttribute(
        "aria-pressed",
        String($("sound-category").value === category),
      );
      const top = el("span");
      top.append(el("span", name), el("strong", `${found} / ${files.length}`));
      const bar = el("progress");
      bar.max = files.length || 1;
      bar.value = found;
      bar.setAttribute(
        "aria-label",
        `${name} : ${found} fichiers retrouvés sur ${files.length}`,
      );
      b.append(top, bar);
      b.onclick = () => {
        $("sound-category").value = category;
        renderSounds();
      };
      chart.append(b);
    }
  }
  function renderSounds() {
    const query = $("sound-search").value.toLocaleLowerCase("fr").trim(),
      category = $("sound-category").value,
      availability = $("sound-availability").value;
    const results = inventory.audio.filter(
      (a) =>
        (category === "all" || a.category === category) &&
        (availability === "all" ||
          a.available === (availability === "found")) &&
        `${a.file} ${audioName(a)} ${a.aliases.join(" ")}`
          .toLocaleLowerCase("fr")
          .includes(query),
    );
    const list = $("sound-list");
    list.replaceChildren();
    results.forEach((a) => list.append(trackRow(a, groups[a.category], true)));
    if (!results.length)
      list.append(
        el(
          "p",
          "Aucun son ne correspond à ces filtres. Essayez un nom de fichier ou une autre famille.",
          "workshop-small",
        ),
      );
    $("sound-results").textContent =
      `${results.length} fichier(s) · ${results.filter((a) => a.available).length} retrouvé(s) · ${results.filter((a) => !a.available).length} à retrouver.`;
    for (const b of $("sound-category-chart").querySelectorAll("button"))
      b.setAttribute("aria-pressed", String(b.dataset.category === category));
    syncAudioButtons();
  }
  function syncAudioButtons() {
    for (const b of document.querySelectorAll("[data-audio-file]")) {
      const playing =
        activeTrack?.file === b.dataset.audioFile &&
        !audio.paused &&
        !audio.ended;
      b.setAttribute("aria-pressed", String(playing));
      b.textContent = b.disabled ? "—" : playing ? "Ⅱ" : "▷";
      b.closest(".archive-track").classList.toggle("is-playing", playing);
    }
  }
  function drawWave() {
    cancelAnimationFrame(waveFrame);
    const canvas = $("restoration-waveform"),
      ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#b7cb84";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (
      analyser &&
      !audio.paused &&
      !reduced.matches &&
      !document.documentElement.classList.contains("motion-paused")
    ) {
      const values = new Uint8Array(analyser.fftSize);
      analyser.getByteTimeDomainData(values);
      for (let i = 0; i < values.length; i++) {
        const x = (i / (values.length - 1)) * canvas.width,
          y = (values[i] / 255) * canvas.height;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
      waveFrame = requestAnimationFrame(drawWave);
    } else {
      ctx.moveTo(0, canvas.height / 2);
      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();
    }
  }
  async function playTrack(track, role) {
    if (!track.available) return;
    if (!track.path.startsWith("assets/sounds/") || track.path.includes(".."))
      return;
    if (activeTrack?.file === track.file && !audio.paused) {
      audio.pause();
      return;
    }
    audio.pause();
    activeTrack = {
      ...track,
      stadium: ["Tactique", "Résolution", "Ambiance"].includes(role),
    };
    audio.src = track.path;
    $("restoration-now-playing").textContent =
      `${audioName(track)} · ${role || groups[track.category] || "Archive"}`;
    $("restoration-audio-status").textContent =
      activeTrack.restored_low_quality
        ? "Chargement de la restauration, qualité basse…"
        : "Chargement du fichier retrouvé…";
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx && !audioContext) {
        audioContext = new AudioCtx();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        const source = audioContext.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(audioContext.destination);
      }
      if (audioContext?.state === "suspended") await audioContext.resume();
      await audio.play();
    } catch {
      $("restoration-audio-status").textContent =
        "La lecture n’a pas démarré. Utilisez les commandes du lecteur pour réessayer.";
      syncAudioButtons();
    }
  }
  audio.addEventListener("playing", () => {
    $("restoration-audio-status").textContent =
      activeTrack?.restored_low_quality
        ? "Restauré, qualité basse. Une meilleure source reste recherchée."
        : "Lecture du fichier retrouvé. Son authenticité reste à comparer aux archives.";
    syncAudioButtons();
    drawWave();
  });
  audio.addEventListener("pause", () => {
    if (activeTrack)
      $("restoration-audio-status").textContent = "Lecture en pause.";
    syncAudioButtons();
    drawWave();
  });
  audio.addEventListener("ended", () => {
    $("restoration-audio-status").textContent =
      "Fin de la piste. Les oreilles sont encore là.";
    syncAudioButtons();
    drawWave();
  });
  audio.addEventListener("error", () => {
    $("restoration-audio-status").textContent =
      "Ce fichier n’est pas lisible ou n’est plus disponible. L’inventaire doit être actualisé.";
    syncAudioButtons();
  });
  reduced.addEventListener("change", drawWave);
  $("motion-toggle")?.addEventListener("click", () => queueMicrotask(drawWave));
  fetch("assets/site/restoration/inventory.json", { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw Error("inventory");
      return r.json();
    })
    .then((data) => {
      inventory = data;
      const summary = data.summary;
      for (const [gender, id] of [
        [1, "character-bodies-men"],
        [2, "character-bodies-women"],
      ]) {
        $(id).textContent =
          `${data.characters.filter((c) => !c.hero && c.gender === gender && c.body_available).length} / 14`;
      }
      $("inventory-note").textContent =
        `Inventaire du ${new Date(data.inventory_date + "T12:00:00Z").toLocaleDateString("fr-FR")} · Fichiers retrouvés, remplacements provisoires et fidélité à vérifier sont distingués.`;
      $("restoration-overview").replaceChildren(
        metric(
          summary.assets_found,
          summary.assets_expected,
          "Total des ressources retrouvées",
          data.asset_groups.map((g) => `${g.label} : ${g.found} / ${g.expected}`).join(" · ") +
            ". Périmètre recensé des ateliers, ressources manquantes comprises ; une ressource retrouvée peut rester à améliorer.",
        ),
        metric(
          summary.bodies_found,
          summary.bodies_expected,
          "Corps animés classiques retrouvés",
          "Crâ H/F, Eniripsa F, Enutrof F et Iop H.",
        ),
        metric(
          summary.geometry_found,
          summary.geometry_expected,
          "Décors 3D originaux retrouvés",
          "Les neuf fonds tactiques sont retrouvés ; les variantes 3D partagent encore le décor de Cania.",
        ),
        metric(
          summary.audio_found,
          summary.audio_expected,
          "Fichiers audio retrouvés, musiques comprises",
          "Musiques manquantes incluses dans le total, chaque fichier compté une seule fois. Une restauration de qualité basse reste à améliorer.",
        ),
      );
      $("pick-classes").onclick = () => setGroup("classes");
      $("pick-heroes").onclick = () => setGroup("heroes");
      document.querySelectorAll("[data-gender]").forEach(
        (b) =>
          (b.onclick = () => {
            state.gender = Number(b.dataset.gender);
            const current = selected();
            state.id =
              inventory.characters.find(
                (c) =>
                  !c.hero &&
                  c.class_id === current.class_id &&
                  c.gender === state.gender,
              )?.id ||
              choices()[0]?.id ||
              state.id;
            renderPicker();
            renderCharacter();
          }),
      );
      $("character-found-only").onchange = () => {
        const list = choices();
        if (list.length && !list.some((c) => c.id === state.id))
          state.id = list[0].id;
        renderPicker();
        renderCharacter();
      };
      document.querySelectorAll("[data-pose]").forEach(
        (b) =>
          (b.onclick = () => {
            state.pose = b.dataset.pose;
            renderCharacter();
          }),
      );
      document.querySelectorAll("[data-facet]").forEach(
        (b) =>
          (b.onclick = () => {
            state.facet = b.dataset.facet;
            renderCharacter();
          }),
      );
      $("character-reset").onclick = resetCharacter;
      $("character-shuffle").onclick = () => {
        const list = choices();
        if (list.length)
          chooseCharacter(list[Math.floor(Math.random() * list.length)].id);
      };
      $("character-ok").onclick = dossier;
      $("character-help").addEventListener("click", () =>
        $("character-dossier-dialog").close(),
      );
      const roster = $("restoration-roster");
      for (const c of inventory.characters
        .filter((c) => !c.hero && c.gender === 1)
        .slice(0, 6)) {
        const b = el("button");
        b.type = "button";
        b.setAttribute("aria-label", `Explorer ${c.name}`);
        const img = el("img");
        img.src = c.poses.default || c.icon;
        img.alt = "";
        img.loading = "lazy";
        b.append(img);
        b.onclick = () => {
          state.group = "classes";
          state.gender = c.gender;
          chooseCharacter(c.id);
        };
        roster.append(b);
      }
      $("show-original").onclick = () => {
        $("character-html").hidden = true;
        $("original-reference").hidden = false;
        $("show-original").setAttribute("aria-pressed", "true");
        $("show-html").setAttribute("aria-pressed", "false");
      };
      $("show-html").onclick = () => {
        $("character-html").hidden = false;
        $("original-reference").hidden = true;
        $("show-original").setAttribute("aria-pressed", "false");
        $("show-html").setAttribute("aria-pressed", "true");
      };
      inventory.stadiums.forEach((s, index) => {
        const b = el("button");
        b.type = "button";
        b.dataset.index = index;
        b.setAttribute("aria-label", `Stade ${s.name}`);
        const img = el("img");
        img.src = s.image;
        img.alt = "";
        img.loading = "lazy";
        img.width = 120;
        img.height = 80;
        b.append(img, el("span", s.name));
        b.onclick = () => changeStadium(index);
        $("stadium-grid").append(b);
      });
      $("stadium-prev").onclick = () => changeStadium(state.stadium - 1);
      $("stadium-next").onclick = () => changeStadium(state.stadium + 1);
      $("stadium-zoom").oninput = () => {
        const v = Number($("stadium-zoom").value);
        $("stadium-image").style.transform = `scale(${v / 100})`;
        $("stadium-zoom-value").value = v + " %";
      };
      document.querySelectorAll("[data-music-kind]").forEach(
        (b) =>
          (b.onclick = () => {
            state.musicKind = b.dataset.musicKind;
            renderStadiumTracks();
          }),
      );
      $("sound-search").addEventListener("input", renderSounds);
      $("sound-category").onchange = renderSounds;
      $("sound-availability").onchange = renderSounds;
      renderPicker();
      renderCharacter();
      renderStadium();
      renderSoundChart();
      renderSounds();
      drawWave();
    })
    .catch((error) => {
      $("inventory-note").textContent =
        "L’inventaire n’a pas pu être chargé. Rechargez la page pour retrouver les ateliers interactifs.";
      console.error("Restoration explorer:", error);
    });
})();
