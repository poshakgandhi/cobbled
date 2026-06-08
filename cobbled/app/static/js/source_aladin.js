// Options for configuring Aladin:
// https://cds-astro.github.io/aladin-lite/global.html#AladinOptions

let aladin;
A.init.then(() => {
    aladin = A.aladin(
        '#aladin-lite-div',
        {
            survey: aladin_survey,
            fov: aladin_fov,
            target: aladin_target,
            cooFrame: "icrsd",
            showCooLocation: false,
            showFrame: false,
            showProjectionControl: false,
            showFullscreenControl: false,
        }
    );
});
