(() => {
  const $ = (id) => document.getElementById(id);
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  if (!reducedMotion.matches)
    document.documentElement.classList.add("js-motion");
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries)
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
    },
    { threshold: 0.08 },
  );
  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
  $("menu-toggle").onclick = () => {
    const open = $("menu-toggle").getAttribute("aria-expanded") !== "true";
    $("menu-toggle").setAttribute("aria-expanded", String(open));
    $("menu-toggle").setAttribute(
      "aria-label",
      open ? "Fermer le menu" : "Ouvrir le menu",
    );
    $("main-nav").classList.toggle("is-open", open);
  };
  $("main-nav").addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      $("main-nav").classList.remove("is-open");
      $("menu-toggle").setAttribute("aria-expanded", "false");
      $("menu-toggle").setAttribute("aria-label", "Ouvrir le menu");
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      $("main-nav").classList.remove("is-open");
      $("menu-toggle").setAttribute("aria-expanded", "false");
    }
  });
  $("motion-toggle").onclick = () => {
    const paused =
      !document.documentElement.classList.contains("motion-paused");
    document.documentElement.classList.toggle("motion-paused", paused);
    $("motion-toggle").setAttribute("aria-pressed", String(paused));
    $("motion-toggle").textContent = paused
      ? "RELANCER LES ANIMATIONS ▷"
      : "METTRE LES ANIMATIONS EN PAUSE Ⅱ";
  };
  const cinematicScenes = [
    [
      "terre-terre",
      "LE CONTACT, C’EST SACRÉ.",
      "Deux tempéraments de Terre. Une façon très personnelle de se dire bonjour.",
    ],
    [
      "terre-feu",
      "ÇA VA CHAUFFER.",
      "Terre contre Feu : la diplomatie prend son après-midi.",
    ],
    [
      "feu-terre",
      "L’ÉCHAUFFEMENT EST FINI.",
      "Les crampons parlent. L’arbitre fait semblant de regarder ailleurs.",
    ],
    [
      "lancer",
      "ENVOYEZ DU LOURD.",
      "Un ballon, un bras, et beaucoup trop de confiance.",
    ],
    [
      "reception-ok-air",
      "DANS LES MAINS. PRESQUE FACILE.",
      "Une réception réussie, dans l’animation plein écran d’origine.",
    ],
    [
      "reception-ratee-air",
      "ÇA, C’ÉTAIT LA TÊTE.",
      "La réception ratée fait aussi partie du patrimoine sportif.",
    ],
    [
      "interception",
      "MERCI POUR LA PASSE.",
      "Intercepter : recevoir un cadeau qui ne vous était pas destiné.",
    ],
    [
      "touchdown",
      "LE BALLON EST RENTRÉ !",
      "L’essai. Ce bref instant où tout le monde vous aime.",
    ],
    [
      "bouftous-contents",
      "LES BOUFTOUS APPROUVENT.",
      "Le public de Cania donne de la voix. Et de la laine.",
    ],
    [
      "foule-contente",
      "LE STADE SE RÉVEILLE.",
      "Une ovation d’époque. Les tribunes ont gardé de la voix.",
    ],
    [
      "crabes-contents",
      "DES PINCES ET DES CRAMPONS.",
      "À la plage aussi, on sait reconnaître un beau geste.",
    ],
    [
      "frigost-content",
      "UNE AMBIANCE À BRISER LA GLACE.",
      "Le public de Frigost vous réserve un accueil presque chaleureux.",
    ],
    [
      "canyon-contents",
      "ÇA RÉSONNE DANS LE CANYON.",
      "Une célébration originale du stade de Kara.",
    ],
    [
      "forest-contents",
      "LA FORÊT FAIT DU BRUIT.",
      "Les tribunes de la forêt ont gardé toute leur animation.",
    ],
    [
      "ballotin-contents",
      "L’AMOUR DU BEAU GESTE.",
      "Le stade de Ballotin célèbre à sa manière.",
    ],
    [
      "pixel-contents",
      "LA FOULE, PIXEL PAR PIXEL.",
      "Une célébration aux petits carrés et aux grandes émotions.",
    ],
    [
      "tuto-terre-feu",
      "LA LEÇON COMMENCE.",
      "Terre et Feu : une démonstration du tutoriel original.",
    ],
    [
      "tuto-feu-terre",
      "TRAVAUX PRATIQUES.",
      "Le tutoriel explique. L’adversaire encaisse.",
    ],
    [
      "tuto-terre-terre",
      "RÉVISION DES FONDAMENTAUX.",
      "La théorie du contact, illustrée par le client Flash d’origine.",
    ],
  ].map(([id, title, description]) => ({
    category: "cinematic",
    title,
    description,
    image: `assets/site/cinematic-${id}.webp`,
    video: `assets/site/cinematic-${id}.mp4`,
  }));
  const scenes = [
    ...cinematicScenes,
    {
      category: "orders",
      title: "LE PLAN ÉTAIT PARFAIT.",
      description:
        "Sélection des joueurs, éléments et ordres sur la grille tactique. C’est après que ça se complique.",
      image: "assets/site/game-orders.webp",
      video: "assets/site/game-orders.mp4",
    },
    {
      category: "resolution",
      title: "ET MAINTENANT… ON ASSUME.",
      description:
        "Les ordres se résolvent sur le terrain en 3D, dans le client du jeu.",
      image: "assets/site/game-resolution.webp",
      video: "assets/site/game-resolution.mp4",
    },
    {
      category: "team",
      title: "LE RECRUTEMENT EST OUVERT.",
      description:
        "Créez l’équipe et choisissez vos joueurs dans l’interface d’origine.",
      image: "assets/site/game-club.png",
    },
    {
      category: "team",
      title: "UNE TENUE. DU CARACTÈRE.",
      description:
        "La personnalisation des personnages, avant de personnaliser les bleus de l’adversaire.",
      image: "assets/site/game-customization.png",
    },
    {
      category: "goultard",
      title: "GOULTARD ENTRE AU VESTIAIRE.",
      description:
        "Son illustration originale est bien là. On vous laisse lui expliquer les règles.",
      image: "assets/site/game-goultard.webp",
    },
    {
      category: "goultard",
      title: "LE VESTIAIRE DES LÉGENDES.",
      description:
        "Goultard, Kriss la Krass, Maude… Les personnages spéciaux retrouvent leurs illustrations d’origine.",
      image: "assets/site/game-legends.webp",
    },
  ];
  const carousel = $("game-carousel"),
    carouselVideo = $("carousel-video");
  let sceneIndex = 0,
    carouselPaused = reducedMotion.matches,
    carouselTimer;
  let carouselInView = true,
    carouselHover = false,
    carouselFocus = false;
  const globalPaused = () =>
    document.documentElement.classList.contains("motion-paused");
  function mayPlay() {
    return (
      !carouselPaused && !globalPaused() && !document.hidden && carouselInView
    );
  }
  function syncCarousel() {
    clearTimeout(carouselTimer);
    if (mayPlay()) {
      if (scenes[sceneIndex].video) carouselVideo.play().catch(() => {});
      if (!carouselHover && !carouselFocus)
        carouselTimer = setTimeout(() => showScene(sceneIndex + 1), 6500);
    } else carouselVideo.pause();
    $("carousel-pause").setAttribute("aria-pressed", String(carouselPaused));
    $("carousel-pause").setAttribute(
      "aria-label",
      carouselPaused ? "Relancer le carrousel" : "Mettre le carrousel en pause",
    );
    $("carousel-pause").textContent = carouselPaused ? "▷" : "Ⅱ";
  }
  function showScene(index, announce = false) {
    sceneIndex = (index + scenes.length) % scenes.length;
    const scene = scenes[sceneIndex];
    carouselVideo.pause();
    $("carousel-image").hidden = false;
    $("carousel-image").src = scene.image;
    $("carousel-image").alt = scene.description;
    carouselVideo.hidden = true;
    if (scene.video) {
      carouselVideo.src = scene.video;
      carouselVideo.poster = scene.image;
      carouselVideo.setAttribute("aria-label", scene.description);
      carouselVideo.load();
    } else {
      carouselVideo.removeAttribute("src");
      carouselVideo.load();
    }
    $("carousel-title").textContent = scene.title;
    $("carousel-description").textContent = scene.description;
    $("carousel-count").textContent =
      `${String(sceneIndex + 1).padStart(2, "0")} / ${scenes.length}`;
    document
      .querySelectorAll("[data-scene]")
      .forEach((button) =>
        button.setAttribute(
          "aria-pressed",
          String(button.dataset.scene === scene.category),
        ),
      );
    if (announce)
      $("carousel-announcement").textContent =
        `${sceneIndex + 1} sur ${scenes.length}. ${scene.title} ${scene.description}`;
    syncCarousel();
  }
  carouselVideo.addEventListener("playing", () => {
    carouselVideo.hidden = false;
    $("carousel-image").hidden = true;
  });
  carouselVideo.addEventListener("loadstart", () => {
    $("carousel-image").hidden = false;
  });
  carouselVideo.addEventListener("error", () => {
    carouselVideo.hidden = true;
    $("carousel-image").hidden = false;
  });
  $("carousel-prev").onclick = () => showScene(sceneIndex - 1, true);
  $("carousel-next").onclick = () => showScene(sceneIndex + 1, true);
  $("carousel-pause").onclick = () => {
    carouselPaused = !carouselPaused;
    syncCarousel();
  };
  document.querySelectorAll("[data-scene]").forEach(
    (button) =>
      (button.onclick = () =>
        showScene(
          scenes.findIndex((scene) => scene.category === button.dataset.scene),
          true,
        )),
  );
  carousel.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    showScene(
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? scenes.length - 1
          : sceneIndex + (event.key === "ArrowRight" ? 1 : -1),
      true,
    );
  });
  let swipeStart;
  stageSwipeSetup();
  function stageSwipeSetup() {
    const area = $("carousel-stage");
    area.addEventListener("pointerdown", (event) => {
      if (!event.target.closest("button"))
        swipeStart = { x: event.clientX, y: event.clientY };
    });
    area.addEventListener("pointerup", (event) => {
      if (!swipeStart) return;
      const dx = event.clientX - swipeStart.x,
        dy = event.clientY - swipeStart.y;
      swipeStart = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5)
        showScene(sceneIndex + (dx < 0 ? 1 : -1), true);
    });
    area.addEventListener("pointercancel", () => {
      swipeStart = null;
    });
  }
  carousel.addEventListener("pointerenter", () => {
    carouselHover = true;
    syncCarousel();
  });
  carousel.addEventListener("pointerleave", () => {
    carouselHover = false;
    syncCarousel();
  });
  carousel.addEventListener("focusin", () => {
    carouselFocus = true;
    syncCarousel();
  });
  carousel.addEventListener("focusout", (event) => {
    if (!carousel.contains(event.relatedTarget)) {
      carouselFocus = false;
      syncCarousel();
    }
  });
  new IntersectionObserver(
    (entries) => {
      carouselInView = entries[0].isIntersecting;
      syncCarousel();
    },
    { threshold: 0.15 },
  ).observe(carousel);
  document.addEventListener("visibilitychange", syncCarousel);
  reducedMotion.addEventListener("change", () => {
    carouselPaused = reducedMotion.matches;
    syncCarousel();
  });
  $("motion-toggle").addEventListener("click", syncCarousel);
  const stage = $("carousel-stage"),
    expand = $("carousel-expand");
  function closeExpanded() {
    if (stage.classList.contains("is-expanded")) carousel.prepend(stage);
    stage.classList.remove("is-expanded");
    expand.setAttribute("aria-label", "Voir les images en grand");
    expand.innerHTML = "⤢ <span>PLEIN ÉCRAN</span>";
  }
  expand.onclick = async () => {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    if (stage.classList.contains("is-expanded")) {
      closeExpanded();
      return;
    }
    try {
      await stage.requestFullscreen();
    } catch {
      document.body.append(stage);
      stage.classList.add("is-expanded");
    }
    expand.setAttribute("aria-label", "Fermer le plein écran");
    expand.innerHTML = "× <span>FERMER</span>";
  };
  stage.addEventListener("keydown", (event) => {
    if (
      stage.classList.contains("is-expanded") &&
      ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
    ) {
      event.preventDefault();
      showScene(
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? scenes.length - 1
            : sceneIndex + (event.key === "ArrowRight" ? 1 : -1),
        true,
      );
    }
  });
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) closeExpanded();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeExpanded();
  });
  showScene(0);

  const screens = {
    team: {
      src: "assets/site/game-team.png",
      alt: "Capture réelle de la composition de l’équipe dans Boufbowl",
      description:
        "Dix joueurs. Un collectif. Quelques ego à faire rentrer dans le vestiaire.",
    },
    customization: {
      src: "assets/site/game-customization.png",
      alt: "Capture réelle de la personnalisation d’un Crâ et de sa tenue",
      description:
        "Des couleurs, un nom, des capacités. Le mauvais goût est une option gratuite.",
    },
    club: {
      src: "assets/site/game-club.png",
      alt: "Capture réelle de l’éditeur du club avec équipe, blason et palette",
      description:
        "Un blason, des couleurs et une identité. Maintenant, il va falloir l’assumer.",
    },
  };
  const tabs = [...document.querySelectorAll("[data-screen]")];
  function selectScreen(button) {
    for (const tab of tabs) {
      const selected = tab === button;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
    const screen = screens[button.dataset.screen];
    $("screen-image").src = screen.src;
    $("screen-image").alt = screen.alt;
    $("screen-description").textContent = screen.description;
    $("game-screen").setAttribute("aria-labelledby", button.id);
  }
  tabs.forEach((button, index) => {
    button.onclick = () => selectScreen(button);
    button.onkeydown = (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft")
        next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next != null) {
        event.preventDefault();
        selectScreen(tabs[next]);
        tabs[next].focus();
      }
    };
  });
  const video = $("archive-video"),
    videoDialog = $("video-dialog");
  document.querySelectorAll("[data-video-open]").forEach(
    (button) =>
      (button.onclick = () => {
        videoDialog.showModal();
        video.play().catch(() => {});
      }),
  );
  videoDialog.addEventListener("close", () => video.pause());
  document.querySelectorAll("[data-archive]").forEach((button) => {
    button.onclick = () => {
      const field = button.dataset.archive === "field";
      video.pause();
      video.src = field
        ? "assets/site/tutorial-field.mp4"
        : "assets/site/tutorial-archive.mp4";
      video.loop = field;
      video.load();
      video.play().catch(() => {});
      document
        .querySelectorAll("[data-archive]")
        .forEach((item) =>
          item.setAttribute("aria-pressed", String(item === button)),
        );
    };
  });

  document
    .querySelectorAll("[data-close-dialog]")
    .forEach(
      (button) => (button.onclick = () => button.closest("dialog").close()),
    );
  document.querySelectorAll("dialog").forEach((dialog) =>
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const r = dialog.getBoundingClientRect();
      if (
        event.clientX < r.left ||
        event.clientX > r.right ||
        event.clientY < r.top ||
        event.clientY > r.bottom
      )
        dialog.close();
    }),
  );
  document.querySelectorAll("[data-volunteer]").forEach(
    (button) =>
      (button.onclick = () => {
        $("volunteer-message").value =
          `Bonjour ! Je souhaite donner un coup de main au retour du Boufbowl.\n\nDomaine : ${button.dataset.volunteer}.\nCe que je peux apporter : …\nMes disponibilités / références : …\n\nPourriez-vous m’indiquer comment participer et, si utile, me donner accès au GitHub privé ?`;
        $("copy-status").textContent = "";
        $("volunteer-dialog").showModal();
      }),
  );
  $("copy-message").onclick = async () => {
    try {
      await navigator.clipboard.writeText($("volunteer-message").value);
      $("copy-status").textContent =
        "Message copié. Il ne reste qu’à le personnaliser et l’envoyer au porteur du projet.";
    } catch {
      $("volunteer-message").focus();
      $("volunteer-message").select();
      $("copy-status").textContent =
        "Sélectionnez et copiez le message avec les commandes de votre appareil.";
    }
  };
  const sounds = ["POUF !", "PAF !", "FAUTE ?", "MÊME PAS MAL.", "ARBITRE !"];
  let hits = 0;
  $("brawl-button").onclick = (event) => {
    const text = sounds[hits++ % sounds.length];
    $("brawl-announcer").textContent =
      text + " Le public approuve ce geste à peu près sportif.";
    const tag = document.createElement("span");
    tag.className = "brawl-pop";
    tag.textContent = text;
    const rect = $("brawl-button").getBoundingClientRect();
    tag.style.left =
      Math.min(innerWidth - 180, Math.max(10, event.clientX || rect.left)) +
      "px";
    tag.style.top = (event.clientY || rect.top) + "px";
    document.body.append(tag);
    const visual = document.querySelector(".hero-art");
    visual.classList.remove("brawl-hit");
    void visual.offsetWidth;
    visual.classList.add("brawl-hit");
    setTimeout(() => tag.remove(), 1100);
  };
  function safeURL(url) {
    try {
      const parsed = new URL(url, location.origin);
      return parsed.protocol === "https:" ||
        (parsed.origin === location.origin &&
          parsed.pathname.startsWith("/downloads/"))
        ? parsed.href
        : null;
    } catch {
      return null;
    }
  }
  fetch("api/site", { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw Error("Site configuration unavailable");
      return r.json();
    })
    .then((data) => {
      for (const [key, id] of [
        ["android", "android"],
        ["desktop", "desktop"],
        ["windows", "windows"],
      ]) {
        const item = data.downloads?.[key],
          url = item?.url && safeURL(item.url);
        if (!url) continue;
        const link = $("download-" + id);
        link.href = url;
        link.textContent =
          key === "android" ? "TÉLÉCHARGER L’APK ↗" : key === "windows" ? "WINDOWS · TÉLÉCHARGER ↗" : "LINUX · TÉLÉCHARGER ↗";
        if (item.local) link.setAttribute("download", "");
        else {
          link.target = "_blank";
          link.rel = "noopener";
        }
        $(id + "-status").textContent = "BUILD DISPONIBLE";
        $(id + "-detail").textContent =
          item.description +
          (item.size ? " · " + (item.size / 1048576).toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " Mo" : "");
      }
      const contact = data.contact_url && safeURL(data.contact_url);
      if (contact) {
        $("contact-project").href = contact;
        document.querySelectorAll("[data-project-contact]").forEach((link) => {
          link.href = contact;
        });
        $("contact-project").hidden = false;
        $("contact-project").textContent = "REJOINDRE DISCORD DOFUS 3 ↗";
        $("contact-detail").textContent =
          "Retrouvez le porteur du projet sur le Discord Dofus 3 pour proposer votre aide et demander un accès au GitHub privé.";
      }
      const source =
        data.tot_quote_source_url && safeURL(data.tot_quote_source_url);
      if (source) {
        const a = document.createElement("a");
        a.href = source;
        a.textContent = "Consulter la source.";
        a.target = "_blank";
        a.rel = "noopener";
        $("quote-source").replaceChildren(a);
      }
    })
    .catch(() => {
      /* The static page remains usable; unconfirmed builds stay on request. */
    });
})();
