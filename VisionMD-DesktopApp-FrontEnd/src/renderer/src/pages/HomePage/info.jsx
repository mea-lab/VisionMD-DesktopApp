export default function Info() {
  return (
    <article className="prose dark:prose-invert max-w-none space-y-4">
      <h1 className="text-xl font-semibold">VisionMD</h1>
      <p>
        VisionMD, an open-source software for automated video-based analysis of MDS-UPDRS Part III motor tasks, 
        offers precise, objective, and scalable assessments of motor symptoms in Parkinson's disease and other 
        movement disorders. Leveraging deep learning, VisionMD tracks body movements to compute kinematic features 
        that quantify symptoms severity and supports longitudinal monitoring. VisionMD's user-friendly, customizable 
        framework empowers clinicians and researchers to objectively evaluate motor symptoms in persons with 
        movement disorders without specialized hardware.
      </p>

      <h1 className="text-xl font-semibold">Tutorials</h1>
      <div className="flex flex-col space-y-8 items-center">
        <iframe
          className="w-full max-w-2xl aspect-video"
          src="https://www.youtube.com/embed/nEziXfARw8o" 
          title="YouTube video player" 
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
          allowfullscreen>
        </iframe>
        <iframe 
          className="w-full max-w-2xl aspect-video"
          src="https://www.youtube.com/embed/jZDgEBjXwP8" 
          title="YouTube video player" 
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
          allowfullscreen>
        </iframe>
      </div>

    </article>
  );
}
