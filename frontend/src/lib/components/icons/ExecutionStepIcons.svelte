<!-- Execution panel: Next, Into, Out, Restart. Renders hidden SVG defs for <use href="#id">. -->
<svg class="icon-sr-only" aria-hidden="true" width="0" height="0">
  <defs>
    <symbol id="icon-step-next" viewBox="0 0 16 16"><path fill="currentColor" d="M2 6h7v4H2V6z M9 4l5 4-5 4V4z"/></symbol>
    <!-- Into & Out: same arrow; Into starts at y=0 so Out tip lands at y=0, clearly outside box (opening at 5) -->
    <symbol id="icon-step-into" viewBox="0 0 16 16">
      <path fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" d="M3 13L13 13 13 5 11 5M3 13 3 5 5 5"/>
      <path fill="currentColor" d="M7 0h2v8h-2zM5 8l3 4 3-4H5z"/>
    </symbol>
    <symbol id="icon-step-out" viewBox="0 0 16 16">
      <path fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" d="M3 13L13 13 13 5 11 5M3 13 3 5 5 5"/>
      <path fill="currentColor" d="M7 0h2v8h-2zM5 8l3 4 3-4H5z" transform="rotate(180 8 6)"/>
    </symbol>
    <!-- Restart: viewBox with padding so arrowhead tip and top are not clipped -->
    <symbol id="icon-step-restart" viewBox="-2 -3 20 19">
      <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="butt" stroke-linejoin="round" d="M14 8 A6 6 0 0 1 8 14 A6 6 0 0 1 2 8 A6 6 0 0 1 8 2"/>
      <path fill="currentColor" d="M8-2v8l6-4-6-4z"/>
    </symbol>
  </defs>
</svg>

<style>
  .icon-sr-only {
    position: absolute;
    width: 0;
    height: 0;
    overflow: hidden;
  }
</style>
