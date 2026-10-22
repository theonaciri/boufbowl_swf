import { assetUrl } from "./tools/website/asset-url.js";

(() => {
  const $ = (id) => document.getElementById(id);
  // Cover crops can paint an image wider than its box. Include that hidden
  // width in source selection so a narrow, tall card does not upscale a small image.
  const coverImages = document.querySelectorAll("img[data-responsive-cover]");
  const sizeCoverImage = (image) => {
    const ratio = Number(image.getAttribute("width")) / Number(image.getAttribute("height"));
    const sizes = `${Math.ceil(Math.max(image.clientWidth, image.clientHeight * ratio))}px`;
    if (image.sizes !== sizes) image.sizes = sizes;
  };
  const coverObserver = new ResizeObserver((entries) => {
    for (const { target } of entries) sizeCoverImage(target);
  });
  for (const image of coverImages) {
    sizeCoverImage(image);
    coverObserver.observe(image);
  }
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
  const puppetVideos = [...document.querySelectorAll("[data-puppet-src]")];
  const puppetToggle = $("puppet-motion-toggle");
  if (puppetVideos.length && puppetToggle) {
    const visiblePuppets = new Set();
    let puppetsPaused = reducedMotion.matches;
    const syncPuppets = () => {
      const globallyPaused = document.documentElement.classList.contains("motion-paused");
      const paused = puppetsPaused || globallyPaused;
      puppetToggle.disabled = globallyPaused;
      puppetToggle.setAttribute("aria-pressed", String(paused));
      puppetToggle.textContent = paused ? "Animer les personnages" : "Mettre les animations en pause";
      for (const video of puppetVideos) {
        const inView = visiblePuppets.has(video) && !document.hidden;
        if (!inView || paused) {
          video.pause();
          // Cancel offscreen downloads; the cached loop is reused on return.
          if (!inView && video.hasAttribute("src")) {
            video.removeAttribute("src");
            video.load();
          }
          continue;
        }
        if (!video.hasAttribute("src")) video.src = assetUrl(video.dataset.puppetSrc);
        video.muted = true;
        video.play().catch(() => {});
      }
    };
    const puppetObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) visiblePuppets.add(entry.target);
        else visiblePuppets.delete(entry.target);
      }
      syncPuppets();
    }, { threshold: 0.01 });
    puppetVideos.forEach((video) => puppetObserver.observe(video));
    puppetToggle.addEventListener("click", () => {
      puppetsPaused = !puppetsPaused;
      syncPuppets();
    });
    document.addEventListener("visibilitychange", syncPuppets);
    $("motion-toggle").addEventListener("click", syncPuppets);
    reducedMotion.addEventListener("change", () => {
      puppetsPaused = reducedMotion.matches;
      syncPuppets();
    });
    syncPuppets();
  }
  const cinematicMediaVersion = "legends-v3";
  const cinematicScenes = [
    [
      "terre-terre",
      "OBJECTIF : MARQUER UN ESSAI",
      "Deux équipes de cinq joueurs s’affrontent. Le but est de porter le ballon jusqu’à la ligne d’en-but adverse.",
    ],
    [
      "terre-feu",
      "PRÉPAREZ VOS ORDRES",
      "À chaque tour, placez vos joueurs sur le terrain hexagonal et choisissez leurs actions avant la résolution du jeu.",
    ],
    [
      "feu-terre",
      "GÉREZ VOS DÉPLACEMENTS",
      "La portée des déplacements dépend des éléments attribués au joueur. Gardez-en assez pour atteindre une position utile.",
    ],
    [
      "lancer",
      "PASSEZ LE BALLON",
      "Une passe permet d’envoyer le ballon à un coéquipier à portée. L’AIR contribue aux actions de lancer et de réception.",
    ],
    [
      "reception-ok-air",
      "RÉUSSISSEZ VOS RÉCEPTIONS",
      "Une passe n’est jamais sûre : le receveur doit être bien placé, et la réussite de la réception dépend de ses caractéristiques.",
    ],
    [
      "reception-ratee-air",
      "RÉCUPÉREZ LE BALLON",
      "Si personne ne maîtrise le ballon, il reste au sol et les joueurs peuvent tenter de le récupérer.",
    ],
    [
      "interception",
      "INTERCEPTEZ LA PASSE",
      "Les adversaires proches peuvent tenter d’intercepter une passe en vol. Placez vos défenseurs sur sa trajectoire.",
    ],
    [
      "touchdown",
      "FRANCHISSEZ L’EN-BUT",
      "Un joueur vivant et non étourdi marque en franchissant la ligne d’en-but adverse avec le ballon.",
    ],
    [
      "masque-reception",
      "ACTIVEZ UN POUVOIR DE CLASSE",
      "Chaque classe dispose d’un pouvoir. Une équipe peut en activer un par tour, au prix de l’action de son lanceur.",
    ],
    [
      "harebourg-lancer",
      "PLACEZ VOTRE RECEVEUR",
      "Choisissez un coéquipier comme cible de la passe et placez-le à portée pour augmenter ses chances de réception.",
    ],
    [
      "pan-diego-interception",
      "COUPEZ LA PASSE",
      "Un défenseur à portée du ballon peut tenter une interception. L’AIR est nécessaire pour tenter une réception en vol.",
    ],
    [
      "ironman-touchdown",
      "GAGNEZ LES DUELS",
      "Les combats peuvent blesser ou éliminer un joueur. Si le porteur est mis hors jeu, il lâche le ballon.",
    ],
    [
      "jack-reception-ratee",
      "PRENEZ GARDE AUX CHUTES",
      "Allonger un déplacement au-delà de la distance sûre augmente le risque de chute : mesurez le gain face au danger.",
    ],
    [
      "armand-reception",
      "GAGNEZ LE MATCH",
      "La victoire revient à l’équipe qui marque le plus d’essais avant la fin du match.",
    ],
    [
      "skunk-lancer",
      "CHANGEZ DE CÔTÉ À LA MI-TEMPS",
      "Le match se joue en deux périodes. À la reprise, les équipes changent de côté pour attaquer l’autre en-but.",
    ],
  ].map(([id, title, description]) => ({
    category: "cinematic",
    title,
    description,
    video: `assets/site/cinematic-${id}-${cinematicMediaVersion}.mp4`,
    videoAv1: `assets/site/cinematic-${id}-${cinematicMediaVersion}.av1.mp4`,
  }));
  const scenes = [
    ...cinematicScenes,
    {
      category: "orders",
      title: "PRÉPAREZ CHAQUE TOUR",
      description:
        "Avant chaque tour, répartissez les éléments de vos joueurs et préparez leurs ordres sur la grille tactique.",
      image: "assets/site/game-orders.webp",
    },
    {
      category: "resolution",
      title: "LES ORDRES SE RÉSOLVENT",
      description:
        "Une fois les ordres des deux équipes validés, déplacements, passes et duels se résolvent sur le terrain.",
      image: "assets/site/game-resolution.webp",
    },
    {
      category: "team",
      title: "CINQ JOUEURS SUR LE TERRAIN",
      description:
        "Chaque équipe aligne cinq joueurs et dispose d’un effectif de dix. Choisissez les profils adaptés à votre stratégie.",
      image: "assets/site/game-club.png",
    },
    {
      category: "team",
      title: "CHOISISSEZ VOS CLASSES",
      description:
        "Les classes ont des caractéristiques différentes : composez votre équipe pour équilibrer déplacement, passe et combat.",
      image: "assets/site/game-customization.png",
    },
    {
      category: "goultard",
      title: "CHAQUE CLASSE A SES FORCES",
      description:
        "Les joueurs spéciaux gardent leur identité, mais suivent les règles de leur classe sur le terrain.",
      image: "assets/site/game-goultard.webp",
    },
    {
      category: "goultard",
      title: "PROTÉGEZ LE PORTEUR",
      description:
        "Une équipe gagne en combinant ses classes, en protégeant le porteur et en ouvrant une voie vers l’en-but.",
      image: "assets/site/game-legends.webp",
    },
  ];
  const carousel = $("game-carousel"),
    carouselVideo = $("carousel-video");
  let sceneIndex = 0,
    carouselPaused = reducedMotion.matches,
    carouselTimer;
  let carouselInView = false,
    carouselHover = false,
    carouselFocus = false;
  const globalPaused = () =>
    document.documentElement.classList.contains("motion-paused");
  function mayPlay() {
    return (
      !carouselPaused && !globalPaused() && !document.hidden && carouselInView
    );
  }
  const failedAv1 = new Set();
  function preferredCarouselVideo(scene) {
    return scene.videoAv1 && !failedAv1.has(scene.videoAv1) &&
      carouselVideo.canPlayType('video/mp4; codecs="av01.0.08M.10"')
      ? scene.videoAv1 : scene.video;
  }
  function syncCarousel() {
    clearTimeout(carouselTimer);
    const scene = scenes[sceneIndex], source = preferredCarouselVideo(scene);
    if (source && carouselInView) {
      if (carouselVideo.dataset.source !== source) {
        carouselVideo.pause();
        carouselVideo.src = assetUrl(source);
        carouselVideo.dataset.source = source;
        carouselVideo.load();
      }
    } else if (carouselVideo.hasAttribute("src")) {
      carouselVideo.pause();
      carouselVideo.removeAttribute("src");
      delete carouselVideo.dataset.source;
      carouselVideo.load();
    }
    if (mayPlay()) {
      if (scene.video) carouselVideo.play().catch(() => {});
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
    $("carousel-image").hidden = !scene.image;
    if (scene.image) {
      $("carousel-image").src = assetUrl(scene.image);
      $("carousel-image").alt = scene.description;
    } else {
      $("carousel-image").removeAttribute("src");
      $("carousel-image").alt = "";
    }
    carouselVideo.hidden = true;
    if (scene.video) carouselVideo.setAttribute("aria-label", scene.description);
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
    $("carousel-image").hidden = !scenes[sceneIndex].image;
  });
  carouselVideo.addEventListener("error", () => {
    const scene = scenes[sceneIndex];
    if (scene.videoAv1 && carouselVideo.dataset.source === scene.videoAv1) {
      failedAv1.add(scene.videoAv1);
      syncCarousel();
      return;
    }
    carouselVideo.hidden = true;
    $("carousel-image").hidden = !scene.image;
  });
  const sounds = ["POUF !", "PAF !", "FAUTE ?", "MÊME PAS MAL.", "ARBITRE !"];
  let hits = 0;
  const playCarouselPouf = (event, button) => {
    const text = sounds[hits++ % sounds.length];
    playPouf(event, button, carousel, text);
  };
  $("carousel-prev").onclick = (event) => {
    playCarouselPouf(event, $("carousel-prev"));
    showScene(sceneIndex - 1, true);
  };
  $("carousel-next").onclick = (event) => {
    playCarouselPouf(event, $("carousel-next"));
    showScene(sceneIndex + 1, true);
  };
  $("carousel-pause").onclick = () => {
    carouselPaused = !carouselPaused;
    syncCarousel();
  };
  document.querySelectorAll("[data-scene]").forEach(
    (button) =>
      (button.onclick = (event) => {
        playCarouselPouf(event, button);
        showScene(
          scenes.findIndex((scene) => scene.category === button.dataset.scene),
          true,
        );
      }),
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
    $("screen-image").src = assetUrl(screen.src);
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
      video.src = assetUrl(field
        ? "assets/site/tutorial-field.mp4"
        : "assets/site/tutorial-archive.mp4");
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
  function playPouf(event, anchor, visual, text = "POUF !") {
    const tag = document.createElement("span");
    tag.className = "brawl-pop";
    tag.textContent = text;
    const rect = anchor.getBoundingClientRect();
    tag.style.left =
      Math.min(innerWidth - 180, Math.max(10, event.clientX || rect.left)) +
      "px";
    tag.style.top = (event.clientY || rect.top) + "px";
    document.body.append(tag);
    visual.classList.remove("brawl-hit");
    void visual.offsetWidth;
    visual.classList.add("brawl-hit");
    setTimeout(() => tag.remove(), 1100);
  }
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
  // Download metadata must match the files published in this static build.
  fetch("resources/site-manifest.json", { cache: "no-store" })
    .then((r) => {
      if (!r.ok) throw Error("Site configuration unavailable");
      return r.json();
    })
    .catch(async () => {
      const response = await fetch("api/site", { cache: "no-store" });
      if (!response.ok) throw Error("Site configuration unavailable");
      return response.json();
    })
    .then((data) => {
      for (const [key, id] of [
        ["android", "android"],
        ["desktop", "desktop"],
        ["windows", "windows"],
      ]) {
        const item = data.downloads?.[key],
          url = item?.url && safeURL(item.url);
        const link = $("download-" + id);
        if (!url) {
          link.removeAttribute("href");
          link.setAttribute("aria-disabled", "true");
          link.textContent = "BUILD INDISPONIBLE";
          $(id + "-status").textContent = "INDISPONIBLE";
          continue;
        }
        link.href = url;
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
