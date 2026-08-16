function e(e,t,o,i){var r,a=arguments.length,s=a<3?t:null===i?i=Object.getOwnPropertyDescriptor(t,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)s=Reflect.decorate(e,t,o,i);else for(var n=e.length-1;n>=0;n--)(r=e[n])&&(s=(a<3?r(s):a>3?r(t,o,s):r(t,o))||s);return a>3&&s&&Object.defineProperty(t,o,s),s}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,o=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),r=new WeakMap;let a=class{constructor(e,t,o){if(this._$cssResult$=!0,o!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(o&&void 0===e){const o=void 0!==t&&1===t.length;o&&(e=r.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),o&&r.set(t,e))}return e}toString(){return this.cssText}};const s=(e,...t)=>{const o=1===e.length?e[0]:t.reduce((t,o,i)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+e[i+1],e[0]);return new a(o,e,i)},n=o?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const o of e.cssRules)t+=o.cssText;return(e=>new a("string"==typeof e?e:e+"",void 0,i))(t)})(e):e,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,g=m.trustedTypes,b=g?g.emptyScript:"",f=m.reactiveElementPolyfillSupport,_=(e,t)=>e,y={toAttribute(e,t){switch(t){case Boolean:e=e?b:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let o=e;switch(t){case Boolean:o=null!==e;break;case Number:o=null===e?null:Number(e);break;case Object:case Array:try{o=JSON.parse(e)}catch(e){o=null}}return o}},v=(e,t)=>!l(e,t),x={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=x){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const o=Symbol(),i=this.getPropertyDescriptor(e,o,t);void 0!==i&&c(this.prototype,e,i)}}static getPropertyDescriptor(e,t,o){const{get:i,set:r}=d(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:i,set(t){const a=i?.call(this);r?.call(this,t),this.requestUpdate(e,a,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??x}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const o of t)this.createProperty(o,e[o])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,o]of t)this.elementProperties.set(e,o)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const o=this._$Eu(e,t);void 0!==o&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const o=new Set(e.flat(1/0).reverse());for(const e of o)t.unshift(n(e))}else void 0!==e&&t.push(n(e));return t}static _$Eu(e,t){const o=t.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const o of t.keys())this.hasOwnProperty(o)&&(e.set(o,this[o]),delete this[o]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,i)=>{if(o)e.adoptedStyleSheets=i.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const o of i){const i=document.createElement("style"),r=t.litNonce;void 0!==r&&i.setAttribute("nonce",r),i.textContent=o.cssText,e.appendChild(i)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,o){this._$AK(e,o)}_$ET(e,t){const o=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,o);if(void 0!==i&&!0===o.reflect){const r=(void 0!==o.converter?.toAttribute?o.converter:y).toAttribute(t,o.type);this._$Em=e,null==r?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(e,t){const o=this.constructor,i=o._$Eh.get(e);if(void 0!==i&&this._$Em!==i){const e=o.getPropertyOptions(i),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:y;this._$Em=i;const a=r.fromAttribute(t,e.type);this[i]=a??this._$Ej?.get(i)??a,this._$Em=null}}requestUpdate(e,t,o,i=!1,r){if(void 0!==e){const a=this.constructor;if(!1===i&&(r=this[e]),o??=a.getPropertyOptions(e),!((o.hasChanged??v)(r,t)||o.useDefault&&o.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(a._$Eu(e,o))))return;this.C(e,t,o)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:o,reflect:i,wrapped:r},a){o&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,a??t??this[e]),!0!==r||void 0!==a)||(this._$AL.has(e)||(this.hasUpdated||o||(t=void 0),this._$AL.set(e,t)),!0===i&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,o]of e){const{wrapped:e}=o,i=this[t];!0!==e||this._$AL.has(t)||void 0===i||this.C(t,void 0,o,i)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[_("elementProperties")]=new Map,$[_("finalized")]=new Map,f?.({ReactiveElement:$}),(m.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,k=e=>e,A=w.trustedTypes,E=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,S="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,z=`<${T}>`,M=document,D=()=>M.createComment(""),I=e=>null===e||"object"!=typeof e&&"function"!=typeof e,O=Array.isArray,P="[ \t\n\f\r]",R=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,F=/>/g,U=RegExp(`>|${P}(?:([^\\s"'>=/]+)(${P}*=${P}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),j=/'/g,H=/"/g,L=/^(?:script|style|textarea|title)$/i,B=(e=>(t,...o)=>({_$litType$:e,strings:t,values:o}))(1),W=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),V=new WeakMap,K=M.createTreeWalker(M,129);function G(e,t){if(!O(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(t):t}class J{constructor({strings:e,_$litType$:t},o){let i;this.parts=[];let r=0,a=0;const s=e.length-1,n=this.parts,[l,c]=((e,t)=>{const o=e.length-1,i=[];let r,a=2===t?"<svg>":3===t?"<math>":"",s=R;for(let t=0;t<o;t++){const o=e[t];let n,l,c=-1,d=0;for(;d<o.length&&(s.lastIndex=d,l=s.exec(o),null!==l);)d=s.lastIndex,s===R?"!--"===l[1]?s=N:void 0!==l[1]?s=F:void 0!==l[2]?(L.test(l[2])&&(r=RegExp("</"+l[2],"g")),s=U):void 0!==l[3]&&(s=U):s===U?">"===l[0]?(s=r??R,c=-1):void 0===l[1]?c=-2:(c=s.lastIndex-l[2].length,n=l[1],s=void 0===l[3]?U:'"'===l[3]?H:j):s===H||s===j?s=U:s===N||s===F?s=R:(s=U,r=void 0);const h=s===U&&e[t+1].startsWith("/>")?" ":"";a+=s===R?o+z:c>=0?(i.push(n),o.slice(0,c)+S+o.slice(c)+C+h):o+C+(-2===c?t:h)}return[G(e,a+(e[o]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),i]})(e,t);if(this.el=J.createElement(l,o),K.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(i=K.nextNode())&&n.length<s;){if(1===i.nodeType){if(i.hasAttributes())for(const e of i.getAttributeNames())if(e.endsWith(S)){const t=c[a++],o=i.getAttribute(e).split(C),s=/([.?@])?(.*)/.exec(t);n.push({type:1,index:r,name:s[2],strings:o,ctor:"."===s[1]?ee:"?"===s[1]?te:"@"===s[1]?oe:Y}),i.removeAttribute(e)}else e.startsWith(C)&&(n.push({type:6,index:r}),i.removeAttribute(e));if(L.test(i.tagName)){const e=i.textContent.split(C),t=e.length-1;if(t>0){i.textContent=A?A.emptyScript:"";for(let o=0;o<t;o++)i.append(e[o],D()),K.nextNode(),n.push({type:2,index:++r});i.append(e[t],D())}}}else if(8===i.nodeType)if(i.data===T)n.push({type:2,index:r});else{let e=-1;for(;-1!==(e=i.data.indexOf(C,e+1));)n.push({type:7,index:r}),e+=C.length-1}r++}}static createElement(e,t){const o=M.createElement("template");return o.innerHTML=e,o}}function X(e,t,o=e,i){if(t===W)return t;let r=void 0!==i?o._$Co?.[i]:o._$Cl;const a=I(t)?void 0:t._$litDirective$;return r?.constructor!==a&&(r?._$AO?.(!1),void 0===a?r=void 0:(r=new a(e),r._$AT(e,o,i)),void 0!==i?(o._$Co??=[])[i]=r:o._$Cl=r),void 0!==r&&(t=X(e,r._$AS(e,t.values),r,i)),t}class Z{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:o}=this._$AD,i=(e?.creationScope??M).importNode(t,!0);K.currentNode=i;let r=K.nextNode(),a=0,s=0,n=o[0];for(;void 0!==n;){if(a===n.index){let t;2===n.type?t=new Q(r,r.nextSibling,this,e):1===n.type?t=new n.ctor(r,n.name,n.strings,this,e):6===n.type&&(t=new ie(r,this,e)),this._$AV.push(t),n=o[++s]}a!==n?.index&&(r=K.nextNode(),a++)}return K.currentNode=M,i}p(e){let t=0;for(const o of this._$AV)void 0!==o&&(void 0!==o.strings?(o._$AI(e,o,t),t+=o.strings.length-2):o._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,o,i){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=o,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=X(this,e,t),I(e)?e===q||null==e||""===e?(this._$AH!==q&&this._$AR(),this._$AH=q):e!==this._$AH&&e!==W&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>O(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==q&&I(this._$AH)?this._$AA.nextSibling.data=e:this.T(M.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:o}=e,i="number"==typeof o?this._$AC(e):(void 0===o.el&&(o.el=J.createElement(G(o.h,o.h[0]),this.options)),o);if(this._$AH?._$AD===i)this._$AH.p(t);else{const e=new Z(i,this),o=e.u(this.options);e.p(t),this.T(o),this._$AH=e}}_$AC(e){let t=V.get(e.strings);return void 0===t&&V.set(e.strings,t=new J(e)),t}k(e){O(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let o,i=0;for(const r of e)i===t.length?t.push(o=new Q(this.O(D()),this.O(D()),this,this.options)):o=t[i],o._$AI(r),i++;i<t.length&&(this._$AR(o&&o._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class Y{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,o,i,r){this.type=1,this._$AH=q,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=r,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=q}_$AI(e,t=this,o,i){const r=this.strings;let a=!1;if(void 0===r)e=X(this,e,t,0),a=!I(e)||e!==this._$AH&&e!==W,a&&(this._$AH=e);else{const i=e;let s,n;for(e=r[0],s=0;s<r.length-1;s++)n=X(this,i[o+s],t,s),n===W&&(n=this._$AH[s]),a||=!I(n)||n!==this._$AH[s],n===q?e=q:e!==q&&(e+=(n??"")+r[s+1]),this._$AH[s]=n}a&&!i&&this.j(e)}j(e){e===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends Y{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===q?void 0:e}}class te extends Y{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==q)}}class oe extends Y{constructor(e,t,o,i,r){super(e,t,o,i,r),this.type=5}_$AI(e,t=this){if((e=X(this,e,t,0)??q)===W)return;const o=this._$AH,i=e===q&&o!==q||e.capture!==o.capture||e.once!==o.once||e.passive!==o.passive,r=e!==q&&(o===q||i);i&&this.element.removeEventListener(this.name,this,o),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ie{constructor(e,t,o){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(e){X(this,e)}}const re={I:Q},ae=w.litHtmlPolyfillSupport;ae?.(J,Q),(w.litHtmlVersions??=[]).push("3.3.2");const se=globalThis;let ne=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,o)=>{const i=o?.renderBefore??t;let r=i._$litPart$;if(void 0===r){const e=o?.renderBefore??null;i._$litPart$=r=new Q(t.insertBefore(D(),e),e,void 0,o??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}};ne._$litElement$=!0,ne.finalized=!0,se.litElementHydrateSupport?.({LitElement:ne});const le=se.litElementPolyfillSupport;le?.({LitElement:ne}),(se.litElementVersions??=[]).push("4.2.2");const ce=e=>(t,o)=>{void 0!==o?o.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},de={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},he=(e=de,t,o)=>{const{kind:i,metadata:r}=o;let a=globalThis.litPropertyMetadata.get(r);if(void 0===a&&globalThis.litPropertyMetadata.set(r,a=new Map),"setter"===i&&((e=Object.create(e)).wrapped=!0),a.set(o.name,e),"accessor"===i){const{name:i}=o;return{set(o){const r=t.get.call(this);t.set.call(this,o),this.requestUpdate(i,r,e,!0,o)},init(t){return void 0!==t&&this.C(i,void 0,e,t),t}}}if("setter"===i){const{name:i}=o;return function(o){const r=this[i];t.call(this,o),this.requestUpdate(i,r,e,!0,o)}}throw Error("Unsupported decorator location: "+i)};function pe(e){return(t,o)=>"object"==typeof o?he(e,t,o):((e,t,o)=>{const i=t.hasOwnProperty(o);return t.constructor.createProperty(o,e),i?Object.getOwnPropertyDescriptor(t,o):void 0})(e,t,o)}function ue(e){return pe({...e,state:!0,attribute:!1})}function me(e,t){if(e instanceof Error)return e.message||t;if("object"==typeof e&&null!==e&&"message"in e){const{message:t}=e;if("string"==typeof t&&t)return t}return t}async function ge(e){return(await e.callWS({type:"abode_security/actions/list"})).actions}async function be(e){return e.callWS({type:"abode_security/modes/list"})}async function fe(e){return(await e.callWS({type:"abode_security/entities/sensors"})).sensors}async function _e(e){return(await e.callWS({type:"abode_security/entities/alarms"})).alarms}async function ye(e,t,o){return e.callWS({type:"abode_security/actions/update",action_id:t,...o})}let ve=0;const xe=[],$e=["a[href]","button:not([disabled])",'input:not([disabled]):not([type="hidden"])',"textarea:not([disabled])","select:not([disabled])",'[tabindex]:not([tabindex="-1"])'].join(",");let we=class extends ne{constructor(){super(...arguments),this.heading="",this.variant="dialog",this.size="sm",this.dismissOnOverlay=!0,this.dismissOnEscape=!0,this._hasFooterContent=!1,this._headingId="abode-modal-heading-"+ ++ve,this._previouslyFocused=null,this._onOverlayClick=e=>{this.dismissOnOverlay&&e.target===e.currentTarget&&this._dismiss()},this._onDocKeydown=e=>{this.dismissOnEscape&&xe[xe.length-1]===this&&"Escape"===e.key&&this._dismiss()},this._onFooterSlotChange=e=>{const t=e.target;this._hasFooterContent=t.assignedElements().length>0},this._onSentinelStartFocus=()=>{this._redirectFocus("last")},this._onSentinelEndFocus=()=>{this._redirectFocus("first")}}_redirectFocus(e){const t=this._getFocusable();if(0===t.length)return void this._focusBox();("first"===e?t[0]:t[t.length-1]).focus()}_getFocusable(){const e=this.shadowRoot?.querySelectorAll('slot:not([name]), slot[name="footer"]');if(!e)return[];const t=[];for(const o of e)for(const e of o.assignedElements({flatten:!0}))e instanceof HTMLElement&&(e.matches($e)&&t.push(e),t.push(...e.querySelectorAll($e)));return t.filter(e=>e.tabIndex>=0)}_focusBox(){const e=this.shadowRoot?.querySelector(".modal-box");e?.focus()}_dismiss(){this.dispatchEvent(new CustomEvent("dismiss",{bubbles:!0,composed:!0}))}connectedCallback(){super.connectedCallback(),null===this._previouslyFocused&&(this._previouslyFocused=document.activeElement),xe.push(this),document.addEventListener("keydown",this._onDocKeydown)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._onDocKeydown);const e=xe.indexOf(this);-1!==e&&xe.splice(e,1);const t=document.activeElement;(!t||t===document.body||this.contains(t))&&this._previouslyFocused?.focus?.(),this._previouslyFocused=null}firstUpdated(){const e=this._getFocusable();e.length>0?e[0].focus():this._focusBox()}render(){return B`
      <div class="modal-overlay" @click=${this._onOverlayClick}>
        <span
          class="focus-sentinel focus-sentinel-start"
          tabindex="0"
          @focus=${this._onSentinelStartFocus}
        ></span>
        <div
          class="modal-box"
          role=${this.variant}
          aria-modal="true"
          aria-labelledby=${this._headingId}
          data-size=${this.size}
          tabindex="-1"
        >
          <h2 id=${this._headingId}>${this.heading}</h2>
          <slot></slot>
          <div class="modal-footer" ?hidden=${!this._hasFooterContent}>
            <slot name="footer" @slotchange=${this._onFooterSlotChange}></slot>
          </div>
        </div>
        <span
          class="focus-sentinel focus-sentinel-end"
          tabindex="0"
          @focus=${this._onSentinelEndFocus}
        ></span>
      </div>
    `}};function ke(e,t,o="unavailable"){return e.states?.[t]?.state??o}function Ae(e){return"unavailable"===e||"unknown"===e}we.styles=s`
    :host {
      display: block;
    }

    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }

    .modal-box {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 24px;
      width: 100%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .modal-box[data-size='sm'] {
      max-width: 400px;
    }

    .modal-box[data-size='lg'] {
      max-width: 600px;
      max-height: 90vh;
      overflow-y: auto;
      border-radius: 12px;
    }

    h2 {
      margin: 0 0 16px 0;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .modal-box[data-size='sm'] h2 {
      font-size: 18px;
    }

    .modal-box[data-size='lg'] h2 {
      font-size: 20px;
      margin-bottom: 24px;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
    }

    .modal-box[data-size='lg'] .modal-footer {
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    ::slotted(p) {
      margin: 0 0 24px 0;
      color: var(--secondary-text-color);
      line-height: 1.5;
    }

    /* Focus sentinels are visually hidden but keep their place in the focus
     * order. When tab focus reaches them, the @focus handlers redirect into
     * the first/last real focusable so focus stays trapped inside the modal. */
    .focus-sentinel {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
    }

    .modal-box:focus {
      outline: none;
    }
  `,e([pe({type:String})],we.prototype,"heading",void 0),e([pe({type:String})],we.prototype,"variant",void 0),e([pe({type:String})],we.prototype,"size",void 0),e([pe({type:Boolean,attribute:"dismiss-on-overlay"})],we.prototype,"dismissOnOverlay",void 0),e([pe({type:Boolean,attribute:"dismiss-on-escape"})],we.prototype,"dismissOnEscape",void 0),e([ue()],we.prototype,"_hasFooterContent",void 0),we=e([ce("abode-modal")],we);const Ee=["standby","home","away"],Se=["mon","tue","wed","thu","fri","sat","sun"];let Ce=class extends ne{constructor(){super(...arguments),this.selected=[],this.disabled=!1}_toggle(e){if(this.disabled)return;const t=this.selected.includes(e)?this.selected.filter(t=>t!==e):[...this.selected,e];this.dispatchEvent(new CustomEvent("change",{detail:{selected:t},bubbles:!0,composed:!0}))}render(){return B`
      <div class="chips" role="group" aria-label="Weekdays">
        ${Se.map(e=>B`
            <button
              type="button"
              class="chip ${this.selected.includes(e)?"active":""}"
              ?disabled=${this.disabled}
              aria-pressed=${this.selected.includes(e)?"true":"false"}
              aria-label=${this._fullName(e)}
              title=${this._fullName(e)}
              @click=${()=>this._toggle(e)}
            >
              ${this._label(e)}
            </button>
          `)}
      </div>
    `}_label(e){return{mon:"M",tue:"T",wed:"W",thu:"T",fri:"F",sat:"S",sun:"S"}[e]}_fullName(e){return{mon:"Monday",tue:"Tuesday",wed:"Wednesday",thu:"Thursday",fri:"Friday",sat:"Saturday",sun:"Sunday"}[e]}};Ce.styles=s`
    :host {
      display: block;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border-radius: 50%;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.15s,
        color 0.15s,
        border-color 0.15s;
    }

    .chip.active {
      background: var(--primary-color, #03a9f4);
      color: white;
      border-color: var(--primary-color, #03a9f4);
    }

    .chip:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .chip:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .chip:not(:disabled):hover:not(.active) {
      background: var(--primary-color, #03a9f4);
      color: white;
      border-color: var(--primary-color, #03a9f4);
      opacity: 0.7;
    }
  `,e([pe({type:Array})],Ce.prototype,"selected",void 0),e([pe({type:Boolean})],Ce.prototype,"disabled",void 0),Ce=e([ce("abode-day-chip-picker")],Ce);let Te=class extends ne{constructor(){super(...arguments),this.canEdit=!1,this._editing=!1,this._draft=null,this._error=null,this._saving=!1}connectedCallback(){super.connectedCallback(),""===this.schedule?.id&&this._startEdit()}_startEdit(){this._editing=!0,this._draft={name:this.schedule.name,weekdays:[...this.schedule.weekdays],arm_time:this.schedule.arm_time,disarm_time:this.schedule.disarm_time,enabled:this.schedule.enabled},this._error=null}_cancel(){this._saving=!1,""!==this.schedule.id?(this._editing=!1,this._draft=null,this._error=null):this.dispatchEvent(new CustomEvent("cancel-new",{detail:{},bubbles:!0,composed:!0}))}_validate(e){return 0===e.weekdays.length?"Pick at least one weekday":e.arm_time===e.disarm_time?"Arm and disarm times must differ":/^([01]\d|2[0-3]):[0-5]\d$/.test(e.arm_time)?/^([01]\d|2[0-3]):[0-5]\d$/.test(e.disarm_time)?(e.name?.length??0)>100?"Name too long (max 100)":null:"Invalid disarm time":"Invalid arm time"}_save(){if(!this._draft)return;const e=this._validate(this._draft);e?this._error=e:(this._error=null,this._saving=!0,this.dispatchEvent(new CustomEvent("save",{detail:{id:this.schedule.id,data:{...this._draft}},bubbles:!0,composed:!0})))}_delete(){this.dispatchEvent(new CustomEvent("delete",{detail:{id:this.schedule.id},bubbles:!0,composed:!0}))}_onDaysChange(e){if(!this._draft)return;const{selected:t}=e.detail;this._draft={...this._draft,weekdays:t},this._error=null}_onArmTimeChange(e){this._draft&&(this._draft={...this._draft,arm_time:e.target.value},this._error=null)}_onDisarmTimeChange(e){this._draft&&(this._draft={...this._draft,disarm_time:e.target.value},this._error=null)}_onNameChange(e){this._draft&&(this._draft={...this._draft,name:e.target.value})}_onEnabledChange(e){this._draft&&(this._draft={...this._draft,enabled:e.target.checked})}render(){return this._editing&&this._draft?this._renderEditMode(this._draft):this._renderViewMode()}_renderViewMode(){const e=this.schedule,t=!e.enabled;return B`
      <div class="row">
        <div class="view-row ${t?"disabled":""}">
          <abode-day-chip-picker .selected=${e.weekdays} .disabled=${!0}></abode-day-chip-picker>
          <span class="time-display">${e.arm_time} → ${e.disarm_time}</span>
          ${e.name?B`<span class="row-name">${e.name}</span>`:q}
          ${e.last_error?B`<span class="error-badge" title=${e.last_error}>⚠ Error</span>`:q}
          <span class="spacer"></span>
          <label class="enable-toggle" title=${e.enabled?"Enabled":"Disabled"}>
            <input
              type="checkbox"
              .checked=${e.enabled}
              ?disabled=${!this.canEdit}
              aria-label=${e.enabled?"Enabled":"Disabled"}
              @change=${this._onViewEnabledChange}
            />
            ${e.enabled?"Enabled":"Disabled"}
          </label>
          ${this.canEdit?B`
                <button
                  type="button"
                  class="icon-button"
                  aria-label="Edit schedule"
                  title="Edit"
                  @click=${this._startEdit}
                >
                  <ha-icon icon="mdi:pencil-outline"></ha-icon>
                </button>
                <button
                  type="button"
                  class="icon-button delete"
                  aria-label="Delete schedule"
                  title="Delete"
                  @click=${this._delete}
                >
                  <ha-icon icon="mdi:trash-can-outline"></ha-icon>
                </button>
              `:q}
        </div>
      </div>
    `}_onViewEnabledChange(e){if(!this.canEdit)return;const t=e.target.checked;this.dispatchEvent(new CustomEvent("save",{detail:{id:this.schedule.id,data:{name:this.schedule.name,weekdays:[...this.schedule.weekdays],arm_time:this.schedule.arm_time,disarm_time:this.schedule.disarm_time,enabled:t}},bubbles:!0,composed:!0}))}_renderEditMode(e){return B`
      <div class="row">
        <div class="edit-form">
          <div class="form-row">
            <abode-day-chip-picker
              .selected=${e.weekdays}
              @change=${this._onDaysChange}
            ></abode-day-chip-picker>
          </div>
          <div class="form-row">
            <label>Arm</label>
            <input
              type="time"
              class="time-input"
              .value=${e.arm_time}
              @change=${this._onArmTimeChange}
              aria-label="Arm time"
            />
            <span class="arrow">→</span>
            <label>Disarm</label>
            <input
              type="time"
              class="time-input"
              .value=${e.disarm_time}
              @change=${this._onDisarmTimeChange}
              aria-label="Disarm time"
            />
          </div>
          <div class="form-row">
            <label>Name</label>
            <input
              type="text"
              class="name-input"
              .value=${e.name??""}
              placeholder="Optional label"
              maxlength="100"
              @input=${this._onNameChange}
              aria-label="Schedule name"
            />
          </div>
          <div class="form-row">
            <label class="enable-toggle">
              <input
                type="checkbox"
                .checked=${e.enabled??!0}
                @change=${this._onEnabledChange}
                aria-label="Enabled"
              />
              Enabled
            </label>
          </div>
          ${this._error?B`<div class="validation-error" role="alert">${this._error}</div>`:q}
          <div class="form-actions">
            <button
              type="button"
              class="btn primary"
              ?disabled=${this._saving}
              @click=${this._save}
            >
              Save
            </button>
            <button type="button" class="btn secondary" @click=${this._cancel}>Cancel</button>
          </div>
        </div>
      </div>
    `}};Te.styles=s`
    :host {
      display: block;
    }

    .row {
      padding: 10px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }

    .row:last-of-type {
      border-bottom: none;
    }

    .view-row {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .view-row.disabled {
      opacity: 0.5;
    }

    .time-display {
      font-size: 14px;
      color: var(--primary-text-color);
      white-space: nowrap;
    }

    .row-name {
      font-size: 13px;
      color: var(--secondary-text-color);
      font-style: italic;
    }

    .error-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 6px;
      background: var(--error-color, #f44336);
      color: white;
      border-radius: 10px;
      font-size: 11px;
      gap: 4px;
    }

    .icon-button {
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 4px;
      color: var(--secondary-text-color);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition:
        color 0.15s,
        background 0.15s;
    }

    .icon-button:hover {
      color: var(--primary-text-color);
      background: var(--secondary-background-color, #f5f5f5);
    }

    .icon-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .icon-button.delete:hover {
      color: var(--error-color, #f44336);
    }

    .icon-button ha-icon {
      --mdc-icon-size: 20px;
    }

    .spacer {
      flex: 1;
    }

    /* Edit form */
    .edit-form {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 4px 0;
    }

    .form-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .form-row label {
      font-size: 13px;
      color: var(--secondary-text-color);
      min-width: 60px;
    }

    .time-input {
      padding: 4px 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
    }

    .time-input:focus {
      outline: 2px solid var(--primary-color, #03a9f4);
      border-color: transparent;
    }

    .name-input {
      padding: 4px 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      width: 180px;
    }

    .name-input:focus {
      outline: 2px solid var(--primary-color, #03a9f4);
      border-color: transparent;
    }

    .arrow {
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .form-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .btn {
      padding: 6px 14px;
      border: none;
      border-radius: 4px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .btn.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .btn.primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    .btn.primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn.secondary {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .btn.secondary:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .btn:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .validation-error {
      font-size: 12px;
      color: var(--error-color, #f44336);
      padding: 2px 0;
    }

    .enable-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      cursor: pointer;
    }

    .enable-toggle input[type='checkbox'] {
      cursor: pointer;
    }
  `,e([pe({attribute:!1})],Te.prototype,"schedule",void 0),e([pe({type:Boolean})],Te.prototype,"canEdit",void 0),e([ue()],Te.prototype,"_editing",void 0),e([ue()],Te.prototype,"_draft",void 0),e([ue()],Te.prototype,"_error",void 0),e([ue()],Te.prototype,"_saving",void 0),Te=e([ce("abode-schedule-row")],Te);let ze=class extends ne{constructor(){super(...arguments),this._schedules=[],this._loading=!0,this._error=null,this._newRow=null,this._confirmDeleteId=null,this._abort=null}connectedCallback(){super.connectedCallback(),this._load()}disconnectedCallback(){this._abort?.abort(),this._abort=null,super.disconnectedCallback()}get _isAdmin(){return Boolean(this.hass.user?.is_admin)}async _load(){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:t}=e;this._loading=!0,this._error=null;try{const e=await async function(e){return(await e.callWS({type:"abode_security/schedules/list"})).schedules}(this.hass);if(t.aborted)return;this._schedules=e}catch(e){if(t.aborted)return;this._error=e instanceof Error?e.message:"Failed to load schedules"}finally{t.aborted||(this._loading=!1)}}_addNewRow(){this._newRow={id:"",name:"",weekdays:[],arm_time:"22:00",disarm_time:"06:00",enabled:!0,created_at:"",last_armed_at:null,last_disarmed_at:null,last_skip_reason:null,last_error:null}}async _onSave(e){const{id:t,data:o}=e.detail;this._error=null;try{if(t){const e=await async function(e,t){const{id:o,...i}=t;return e.callWS({type:"abode_security/schedules/update",schedule_id:o,...i})}(this.hass,{id:t,...o});this._schedules=this._schedules.map(o=>o.id===t?e:o)}else{const e=await async function(e,t){return e.callWS({type:"abode_security/schedules/create",...t})}(this.hass,o);this._schedules=[...this._schedules,e],this._newRow=null}}catch(e){this._error=e instanceof Error?e.message:"Failed to save schedule"}}_onDeleteRequest(e){const{id:t}=e.detail;this._confirmDeleteId=t}async _confirmDelete(){const e=this._confirmDeleteId;if(e){this._confirmDeleteId=null,this._error=null;try{await async function(e,t){await e.callWS({type:"abode_security/schedules/delete",schedule_id:t})}(this.hass,e),this._schedules=this._schedules.filter(t=>t.id!==e)}catch(e){this._error=e instanceof Error?e.message:"Failed to delete schedule"}}}render(){return B`
      <section
        aria-labelledby="schedules-heading"
        @save=${this._onSave}
        @delete=${this._onDeleteRequest}
        @cancel-new=${()=>{this._newRow=null}}
      >
        <h2 id="schedules-heading" class="section-heading">Home schedules</h2>

        ${this._loading?B`<div class="loading">Loading…</div>`:q}
        ${this._error?B`<div role="alert" class="error-banner">${this._error}</div>`:q}
        ${this._loading||0!==this._schedules.length||this._newRow?q:B`<p class="empty-state">No schedules yet. Add one to arm Home automatically.</p>`}
        ${this._schedules.map(e=>B`
            <abode-schedule-row .schedule=${e} .canEdit=${this._isAdmin}></abode-schedule-row>
          `)}
        ${this._newRow?B`
              <abode-schedule-row .schedule=${this._newRow} .canEdit=${!0}></abode-schedule-row>
            `:q}
        ${this._isAdmin&&!this._newRow?B` <button class="add-button" @click=${this._addNewRow}>+ Add schedule</button> `:q}
      </section>

      ${this._confirmDeleteId?this._renderDeleteConfirm():q}
    `}_renderDeleteConfirm(){return B`
      <abode-modal
        heading="Delete schedule?"
        variant="alertdialog"
        @dismiss=${()=>{this._confirmDeleteId=null}}
      >
        <p>
          This will stop the automatic arming at the configured times. The action does not affect
          the current panel state.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${()=>{this._confirmDeleteId=null}}
        >
          Cancel
        </button>
        <button slot="footer" class="dialog-button danger" @click=${this._confirmDelete}>
          Delete
        </button>
      </abode-modal>
    `}};ze.styles=s`
    :host {
      display: block;
      margin-top: 24px;
    }

    .section-heading {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 0 0 12px 0;
    }

    .loading {
      color: var(--secondary-text-color);
      font-size: 14px;
    }

    .error-banner {
      padding: 10px 14px;
      background: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
      font-size: 14px;
      margin-bottom: 12px;
    }

    .empty-state {
      color: var(--secondary-text-color);
      font-size: 14px;
      font-style: italic;
      padding: 8px 0;
    }

    .add-button {
      margin-top: 12px;
      padding: 6px 14px;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      background: transparent;
      color: var(--primary-color, #03a9f4);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.15s,
        color 0.15s;
    }

    .add-button:hover {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .add-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    /* Confirm-delete dialog buttons */
    .dialog-button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }

    .dialog-button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .dialog-button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .dialog-button.danger {
      background: var(--error-color, #f44336);
      color: white;
    }

    .dialog-button.danger:hover {
      background: var(--error-color, #f44336);
      opacity: 0.85;
    }

    .dialog-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }
  `,e([pe({attribute:!1})],ze.prototype,"hass",void 0),e([ue()],ze.prototype,"_schedules",void 0),e([ue()],ze.prototype,"_loading",void 0),e([ue()],ze.prototype,"_error",void 0),e([ue()],ze.prototype,"_newRow",void 0),e([ue()],ze.prototype,"_confirmDeleteId",void 0),ze=e([ce("abode-schedules-section")],ze);const Me={disarmed:"standby",armed_home:"home",armed_away:"away"};let De=class extends ne{constructor(){super(...arguments),this._modes=[],this._actions=[],this._loading=!0,this._error=null,this._panelEntityId=null,this._confirmMode=null,this._targetMode=null,this._setError=null,this._pendingTimer=null,this._abort=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}disconnectedCallback(){this._abort?.abort(),this._abort=null,this._clearPendingTimer(),super.disconnectedCallback()}async _loadData(){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:t}=e;this._loading=!0,this._error=null;try{const[e,o]=await Promise.all([be(this.hass),ge(this.hass)]);if(t.aborted)return;this._modes=e.modes,this._panelEntityId=e.panel_entity_id??null,this._actions=o}catch(e){if(t.aborted)return;this._error=e instanceof Error?e.message:"Failed to load data"}finally{t.aborted||(this._loading=!1)}}_liveActiveMode(){if(!this._panelEntityId)return null;const e=this.hass.states?.[this._panelEntityId]?.state;return e?Me[e]??null:null}_activeMode(){const e=this._liveActiveMode();return null!==e?e:this._modes.find(e=>e.active)?.id??null}_clearPendingTimer(){null!==this._pendingTimer&&(clearTimeout(this._pendingTimer),this._pendingTimer=null)}_resetPending(){this._targetMode=null,this._clearPendingTimer()}willUpdate(e){null!==this._targetMode&&this._liveActiveMode()===this._targetMode&&this._resetPending()}_getActionsForMode(e){return this._actions.filter(t=>t.modes.includes(e)).sort((e,t)=>Number(t.enabled)-Number(e.enabled))}_renderActionCountBadge(e){const t=e.action_count,o=e.disabled_action_count??0;return t>0&&o>0?B`<span class="badge">${t} active, ${o} disabled</span>`:0===t&&o>0?B`<span class="badge">${o} disabled</span>`:B`<span class="badge">${t} ${1===t?"action":"actions"}</span>`}_requestSwitch(e){this._activeMode()===e.id&&null===this._targetMode||(this._setError=null,this._confirmMode=e)}async _confirmSwitch(){if(!this._confirmMode)return;const e=this._confirmMode;this._confirmMode=null,this._targetMode=e.id,this._setError=null,this._clearPendingTimer(),this._pendingTimer=setTimeout(()=>{this._pendingTimer=null,this._targetMode=null},9e4);try{await async function(e,t){await e.callWS({type:"abode_security/modes/set",mode_id:t})}(this.hass,e.id)}catch(t){return console.error("Failed to set mode:",t),void(this._targetMode===e.id&&(this._setError="Failed to change mode",this._resetPending()))}}render(){return this._loading?B`<div class="loading">Loading modes...</div>`:this._error?B`<div class="error" role="alert">${this._error}</div>`:B`
      ${this._setError?B`
            <div class="operation-error" role="alert">
              ${this._setError}
              <button
                class="dismiss-error"
                @click=${()=>this._setError=null}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          `:""}

      <div class="modes-grid">${this._modes.map(e=>this._renderModeCard(e))}</div>

      <abode-schedules-section .hass=${this.hass}></abode-schedules-section>

      ${this._confirmMode?this._renderConfirmDialog(this._confirmMode):""}
    `}_renderConfirmDialog(e){return B`
      <abode-modal
        heading="Switch mode?"
        variant="alertdialog"
        @dismiss=${()=>this._confirmMode=null}
      >
        <p>
          Switch the system to <strong>${e.name}</strong>? This changes the live arming state
          and runs any actions configured for this mode.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${()=>this._confirmMode=null}
        >
          Cancel
        </button>
        <button slot="footer" class="dialog-button primary" @click=${this._confirmSwitch}>
          Switch
        </button>
      </abode-modal>
    `}_renderModeCard(e){const t=this._getActionsForMode(e.id),o=this._activeMode()===e.id,i=this._targetMode===e.id,r=o&&null===this._targetMode;return B`
      <div class="mode-card ${o?"active":""}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${e.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${e.name}</h3>
            <div class="badges">
              ${this._renderActionCountBadge(e)}
              ${o?B`<span class="badge active">Active</span>`:""}
            </div>
          </div>
        </div>

        ${t.length>0?B`
              <ul class="action-list" aria-label="Actions for ${e.name} mode">
                ${t.map(e=>B`
                    <li class=${e.enabled?q:"disabled"}>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${e.name}
                      ${e.enabled?q:B`<span class="disabled-tag">Disabled</span>`}
                    </li>
                  `)}
              </ul>
            `:B`<div class="empty-actions">No actions configured</div>`}
        ${r?B`<div class="current-mode-label">Current mode</div>`:B`
              <button
                class="switch-button"
                ?disabled=${i}
                aria-label=${`Switch to ${e.name} mode`}
                @click=${()=>this._requestSwitch(e)}
              >
                ${i?`Switching to ${e.name}…`:`Switch to ${e.name}`}
              </button>
            `}
      </div>
    `}};De.styles=s`
    :host {
      display: block;
    }

    .modes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }

    .mode-card {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      border: 2px solid transparent;
      transition:
        border-color 0.2s,
        box-shadow 0.2s;
    }

    .mode-card.active {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 4px 12px rgba(3, 169, 244, 0.2);
    }

    .mode-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }

    .mode-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 50%;
    }

    .mode-icon ha-icon {
      --mdc-icon-size: 20px;
    }

    .mode-info h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      text-transform: capitalize;
    }

    .badges {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 12px;
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .badge.active {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .action-list {
      margin: 12px 0 0 0;
      padding: 0;
      list-style: none;
    }

    .action-list li {
      padding: 6px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .action-list li:last-child {
      border-bottom: none;
    }

    .action-list li ha-icon {
      --mdc-icon-size: 16px;
      color: var(--secondary-text-color);
    }

    .action-list li.disabled {
      color: var(--secondary-text-color);
      opacity: 0.75;
    }

    .action-list .disabled-tag {
      margin-left: auto;
      padding: 1px 6px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 10px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .empty-actions {
      padding: 12px 0;
      color: var(--secondary-text-color);
      font-size: 14px;
      font-style: italic;
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .error {
      padding: 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
    }

    .operation-error {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .dismiss-error {
      background: transparent;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
      opacity: 0.8;
    }

    .dismiss-error:hover {
      opacity: 1;
    }

    .switch-button {
      width: 100%;
      margin-top: 12px;
      padding: 8px 14px;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      background: transparent;
      color: var(--primary-color, #03a9f4);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition:
        background 0.2s,
        color 0.2s;
    }

    .switch-button:hover:not(:disabled) {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .switch-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }

    .switch-button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .current-mode-label {
      margin-top: 12px;
      padding: 8px 14px;
      text-align: center;
      font-size: 12px;
      color: var(--secondary-text-color);
      font-style: italic;
    }

    /* Confirm dialog button styles — applied to <button slot="footer"> inside <abode-modal>. */
    .dialog-button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .dialog-button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .dialog-button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .dialog-button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .dialog-button.primary:hover {
      background: var(--primary-color-dark, #0288d1);
    }
  `,e([pe({attribute:!1})],De.prototype,"hass",void 0),e([ue()],De.prototype,"_modes",void 0),e([ue()],De.prototype,"_actions",void 0),e([ue()],De.prototype,"_loading",void 0),e([ue()],De.prototype,"_error",void 0),e([ue()],De.prototype,"_panelEntityId",void 0),e([ue()],De.prototype,"_confirmMode",void 0),e([ue()],De.prototype,"_targetMode",void 0),e([ue()],De.prototype,"_setError",void 0),De=e([ce("abode-modes-tab")],De);const Ie=2;let Oe=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,o){this._$Ct=e,this._$AM=t,this._$Ci=o}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};const{I:Pe}=re,Re=e=>e,Ne=()=>document.createComment(""),Fe=(e,t,o)=>{const i=e._$AA.parentNode,r=void 0===t?e._$AB:t._$AA;if(void 0===o){const t=i.insertBefore(Ne(),r),a=i.insertBefore(Ne(),r);o=new Pe(t,a,e,e.options)}else{const t=o._$AB.nextSibling,a=o._$AM,s=a!==e;if(s){let t;o._$AQ?.(e),o._$AM=e,void 0!==o._$AP&&(t=e._$AU)!==a._$AU&&o._$AP(t)}if(t!==r||s){let e=o._$AA;for(;e!==t;){const t=Re(e).nextSibling;Re(i).insertBefore(e,r),e=t}}}return o},Ue=(e,t,o=e)=>(e._$AI(t,o),e),je={},He=(e,t=je)=>e._$AH=t,Le=e=>{e._$AR(),e._$AA.remove()},Be=(e,t,o)=>{const i=new Map;for(let r=t;r<=o;r++)i.set(e[r],r);return i},We=(e=>(...t)=>({_$litDirective$:e,values:t}))(class extends Oe{constructor(e){if(super(e),e.type!==Ie)throw Error("repeat() can only be used in text expressions")}dt(e,t,o){let i;void 0===o?o=t:void 0!==t&&(i=t);const r=[],a=[];let s=0;for(const t of e)r[s]=i?i(t,s):s,a[s]=o(t,s),s++;return{values:a,keys:r}}render(e,t,o){return this.dt(e,t,o).values}update(e,[t,o,i]){const r=(e=>e._$AH)(e),{values:a,keys:s}=this.dt(t,o,i);if(!Array.isArray(r))return this.ut=s,a;const n=this.ut??=[],l=[];let c,d,h=0,p=r.length-1,u=0,m=a.length-1;for(;h<=p&&u<=m;)if(null===r[h])h++;else if(null===r[p])p--;else if(n[h]===s[u])l[u]=Ue(r[h],a[u]),h++,u++;else if(n[p]===s[m])l[m]=Ue(r[p],a[m]),p--,m--;else if(n[h]===s[m])l[m]=Ue(r[h],a[m]),Fe(e,l[m+1],r[h]),h++,m--;else if(n[p]===s[u])l[u]=Ue(r[p],a[u]),Fe(e,r[h],r[p]),p--,u++;else if(void 0===c&&(c=Be(s,u,m),d=Be(n,h,p)),c.has(n[h]))if(c.has(n[p])){const t=d.get(s[u]),o=void 0!==t?r[t]:null;if(null===o){const t=Fe(e,r[h]);Ue(t,a[u]),l[u]=t}else l[u]=Ue(o,a[u]),Fe(e,r[h],o),r[t]=null;u++}else Le(r[p]),p--;else Le(r[h]),h++;for(;u<=m;){const t=Fe(e,l[m+1]);Ue(t,a[u]),l[u++]=t}for(;h<=p;){const e=r[h++];null!==e&&Le(e)}return this.ut=s,He(e,l),W}});function qe(e,t){return e.includes(t)?e.filter(e=>e!==t):[...e,t]}const Ve=new Map(["door","window","motion","person","vehicle","animal","object","package","face","visitor","smoke_alarm","co_alarm","speaking","barking","baby_cry","glass_break","siren","smoke","gas","carbon_monoxide","moisture"].map((e,t)=>[e,t]));function Ke(e,t){return(Ve.get(e)??Number.MAX_SAFE_INTEGER)-(Ve.get(t)??Number.MAX_SAFE_INTEGER)||e.localeCompare(t)}const Ge={door:{on:"open",off:"closed"},window:{on:"open",off:"closed"},garage_door:{on:"open",off:"closed"},opening:{on:"open",off:"closed"},motion:{on:"detected",off:"clear"},occupancy:{on:"detected",off:"clear"},presence:{on:"detected",off:"clear"},moisture:{on:"wet",off:"dry"},smoke:{on:"detected",off:"clear"},gas:{on:"detected",off:"clear"},carbon_monoxide:{on:"detected",off:"clear"},person:{on:"detected",off:"clear"},vehicle:{on:"detected",off:"clear"},animal:{on:"detected",off:"clear"},object:{on:"detected",off:"clear"},package:{on:"detected",off:"clear"},face:{on:"detected",off:"clear"},visitor:{on:"detected",off:"clear"},smoke_alarm:{on:"detected",off:"clear"},co_alarm:{on:"detected",off:"clear"},speaking:{on:"detected",off:"clear"},barking:{on:"detected",off:"clear"},baby_cry:{on:"detected",off:"clear"},glass_break:{on:"detected",off:"clear"},siren:{on:"detected",off:"clear"}},Je={person:"Person detected",vehicle:"Vehicle detected",animal:"Animal detected",object:"Object detected",package:"Package detected",face:"Face detected",visitor:"Visitor",smoke_alarm:"Smoke alarm detected",co_alarm:"CO alarm detected",speaking:"Speaking detected",barking:"Barking detected",baby_cry:"Baby cry detected",glass_break:"Glass break detected",siren:"Siren detected"};let Xe=class extends ne{constructor(){super(...arguments),this.action=null,this._name="",this._modes=[],this._delaySeconds=0,this._selectedSensors=[],this._selectedAlarms=[],this._sensors=null,this._alarms=[],this._errors={},this._saving=!1,this._loading=!0,this._loadError=null,this._confirmNotificationOnly=!1,this._expandedCategories=new Set,this._sensorSearch="",this._abort=null}async connectedCallback(){super.connectedCallback(),this._confirmNotificationOnly=!1,this.action&&this._populateForm(),await this._loadEntities()}disconnectedCallback(){this._abort?.abort(),this._abort=null,super.disconnectedCallback()}async _loadEntities(){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:t}=e;this._loading=!0,this._loadError=null;try{const[e,o]=await Promise.all([fe(this.hass),_e(this.hass)]);if(t.aborted)return;if(this._sensors=e,this._alarms=o,this.action&&this._selectedSensors.length>0){const t=new Set;for(const[o,i]of Object.entries(e))(i??[]).some(e=>this._selectedSensors.includes(e.entity_id))&&t.add(o);this._expandedCategories=t}}catch(e){if(t.aborted)return;this._loadError=e instanceof Error?e.message:"Failed to load sensors and alarms"}finally{t.aborted||(this._loading=!1)}}_populateForm(){this.action&&(this._name=this.action.name,this._modes=[...this.action.modes],this._delaySeconds=this.action.delay_seconds,this._selectedSensors=[...this.action.sensor_entity_ids],this._selectedAlarms=this.action.alarm_entity_ids.slice(0,1))}_toggleMode(e){this._modes=qe(this._modes,e),this._clearError("modes")}_toggleSensor(e){this._selectedSensors=qe(this._selectedSensors,e),this._clearError("sensors")}_openMoreInfo(e,t){t.stopPropagation(),this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}_selectAlarm(e){this._selectedAlarms=[e],this._clearError("alarms")}_clearAlarmSelection(){this._selectedAlarms=[],this._confirmNotificationOnly=!1,this._clearError("alarms")}_isCategorySelected(e,t){if(!this._sensors)return!1;const o=t??this._sensors[e]??[];return 0!==o.length&&o.every(e=>this._selectedSensors.includes(e.entity_id))}_isCategoryPartial(e,t){if(!this._sensors)return!1;const o=t??this._sensors[e]??[];if(0===o.length)return!1;const i=o.filter(e=>this._selectedSensors.includes(e.entity_id));return i.length>0&&i.length<o.length}_toggleCategory(e,t){if(!this._sensors)return;const o=t??this._sensors[e]??[],i=o.map(e=>e.entity_id);if(this._isCategorySelected(e,o))this._selectedSensors=this._selectedSensors.filter(e=>!i.includes(e));else{const e=i.filter(e=>!this._selectedSensors.includes(e));this._selectedSensors=[...this._selectedSensors,...e]}this._clearError("sensors")}_toggleCategoryExpanded(e){const t=new Set(this._expandedCategories);t.has(e)?t.delete(e):t.add(e),this._expandedCategories=t}_clearError(e){if(this._errors[e]){const{[e]:t,...o}=this._errors;this._errors=o}}_validate(){return this._errors={},this._name.trim()||(this._errors={...this._errors,name:"Name is required"}),0===this._modes.length&&(this._errors={...this._errors,modes:"Select at least one mode"}),0===this._selectedSensors.length&&(this._errors={...this._errors,sensors:"Select at least one sensor"}),0===Object.keys(this._errors).length}async _handleSave(){if(!this._saving&&this._validate())if(0!==this._selectedAlarms.length||this._confirmNotificationOnly){this._saving=!0;try{const e={name:this._name.trim(),modes:this._modes,delay_seconds:this._delaySeconds,sensor_entity_ids:this._selectedSensors,alarm_entity_ids:this._selectedAlarms};this.action?await ye(this.hass,this.action.id,e):await async function(e,t){return e.callWS({type:"abode_security/actions/create",...t})}(this.hass,e),this.dispatchEvent(new CustomEvent("save"))}catch(e){console.error("Failed to save action:",e),this._errors={...this._errors,form:me(e,"Failed to save")}}finally{this._saving=!1}}else this._confirmNotificationOnly=!0}_handleCancel(){this.dispatchEvent(new CustomEvent("cancel"))}render(){return B`
      <abode-modal
        heading=${this.action?"Edit Action":"New Action"}
        size="lg"
        @dismiss=${this._handleCancel}
      >
        ${this._loading?B`<div class="loading">Loading...</div>`:this._loadError?this._renderLoadError():this._renderFormBody()}
        ${this._loading||this._loadError?"":this._renderFooter()}
      </abode-modal>
    `}_renderLoadError(){return B`
      <div class="retry-row" role="alert">
        <span class="error-text">${this._loadError}</span>
        <button type="button" @click=${this._loadEntities}>Retry</button>
      </div>
    `}_renderFormBody(){return B`
      <div class="form-group">
        <label for="action-name">Name</label>
        <input
          id="action-name"
          type="text"
          .value=${this._name}
          @input=${e=>{this._name=e.target.value,this._clearError("name")}}
          class=${this._errors.name?"error":""}
          placeholder="Enter action name"
        />
        ${this._errors.name?B`<span class="error-text">${this._errors.name}</span>`:""}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${Ee.map(e=>B`
              <label>
                <input
                  type="checkbox"
                  .checked=${this._modes.includes(e)}
                  @change=${()=>this._toggleMode(e)}
                />
                ${e.charAt(0).toUpperCase()+e.slice(1)}
              </label>
            `)}
        </div>
        ${this._errors.modes?B`<span class="error-text">${this._errors.modes}</span>`:""}
      </div>

      <div class="form-group">
        <label>Delay before triggering</label>
        <div class="delay-control">
          <input
            type="range"
            min="0"
            max="60"
            .value=${String(this._delaySeconds)}
            @input=${e=>{this._delaySeconds=Number(e.target.value)}}
          />
          <span class="delay-value">${this._delaySeconds}s</span>
        </div>
      </div>

      <div class="form-group">
        <label>Sensors (at least one required)</label>
        ${this._renderSensorSelection()}
        ${this._errors.sensors?B`<span class="error-text">${this._errors.sensors}</span>`:""}
      </div>

      <div class="form-group">
        <label>Alarm to trigger (optional)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms?B`<span class="error-text">${this._errors.alarms}</span>`:""}
      </div>

      ${this._errors.form?B`<div class="error-text" style="margin-bottom: 16px;">${this._errors.form}</div>`:""}
    `}_renderFooter(){const e=this._confirmNotificationOnly&&0===this._selectedAlarms.length;return B`
      ${e?B`
            <div slot="footer" class="notify-only-confirm" role="alert">
              <ha-icon icon="mdi:alert" aria-hidden="true"></ha-icon>
              <span>
                No alarm selected — this action will only send a notification. It will
                <strong>not</strong> raise an alarm or contact your monitoring service. Press Save
                again to confirm.
              </span>
            </div>
          `:""}
      <button slot="footer" class="cancel" @click=${this._handleCancel}>Cancel</button>
      <button slot="footer" class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
        ${this._saving?"Saving...":e?"Save anyway":"Save"}
      </button>
    `}_renderSensorSelection(){const e=this._sensors;if(!e)return B`<div class="loading">Loading sensors...</div>`;const t=Object.keys(e).filter(t=>(e[t]??[]).length>0).sort(Ke);if(0===t.length)return B`<div class="loading">No sensors available</div>`;const o=this._sensorSearch.trim().toLowerCase(),i=o.length>0,r=e=>Ae(ke(this.hass,e.entity_id,e.state)),a=t.map(t=>{const a=e[t]??[],s=i?a.filter(e=>e.name.toLowerCase().includes(o)):a,n=s.filter(e=>!r(e)),l=s.filter(e=>r(e)),c=[...n,...l],d=a.filter(r).length;return{category:t,sensors:a,filtered:s,ordered:c,unavailableTotal:d}}).filter(({filtered:e})=>!i||e.length>0),s=B`
      <input
        type="search"
        class="sensor-search"
        aria-label="Search sensors"
        placeholder="Search sensors…"
        autocomplete="off"
        spellcheck="false"
        .value=${this._sensorSearch}
        @input=${e=>{this._sensorSearch=e.target.value}}
      />
    `;return 0===a.length?B`
        ${s}
        <div class="loading">No sensors match “${this._sensorSearch}”</div>
      `:B`
      ${s}
      <div class="sensor-categories">
        ${a.map(({category:e,sensors:t,filtered:o,ordered:r,unavailableTotal:a},s)=>{const n=`sensor-cat-${s}-${e.replace(/[^A-Za-z0-9_-]/g,"-")}`,l=Je[e]??e.replace(/_/g," "),c=i||this._expandedCategories.has(e),d=o.length===t.length?`(${t.length})`:`(${o.length}/${t.length})`,h=a>0?B` <span class="unavailable-count">${a} unavailable</span>`:q;return B`
              <div class="category">
                <div
                  class="category-header"
                  @click=${()=>this._toggleCategory(e,o)}
                >
                  <input
                    type="checkbox"
                    .checked=${this._isCategorySelected(e,o)}
                    .indeterminate=${this._isCategoryPartial(e,o)}
                    @click=${e=>e.stopPropagation()}
                    @change=${()=>this._toggleCategory(e,o)}
                  />
                  <span>${l} ${d}${h}</span>
                  ${i?null:B`
                        <button
                          type="button"
                          class="disclosure"
                          aria-expanded=${c?"true":"false"}
                          aria-controls=${c?n:q}
                          aria-label=${c?`Collapse ${l}`:`Expand ${l}`}
                          @click=${t=>{t.stopPropagation(),this._toggleCategoryExpanded(e)}}
                        >
                          <span aria-hidden="true">▸</span>
                        </button>
                      `}
                </div>
                ${c?B`
                      <div id=${n} class="category-items">
                        ${r.map(t=>this._renderSensorRow(t,e))}
                      </div>
                    `:null}
              </div>
            `})}
      </div>
    `}_renderSensorRow(e,t){const o=ke(this.hass,e.entity_id,e.state),i=Ae(o),r=i?"unavailable":"on"===o?"on":"off",a=function(e,t){if(Ae(e))return"unavailable";const o=Ge[t];return o?"on"===e?o.on:"off"===e?o.off:e:e}(o,t);return B`
      <div class="sensor-row ${i?"unavailable":""}">
        <label>
          <input
            type="checkbox"
            .checked=${this._selectedSensors.includes(e.entity_id)}
            @change=${()=>this._toggleSensor(e.entity_id)}
          />
          <span class="entity-name">${e.name}</span>
          <!-- Area column always rendered (even when empty) so the
               state-pill column lines up across rows that do and don't
               have an area assigned. Empty cells get aria-hidden="true"
               so screen readers skip them — the cell exists only for
               layout, not for semantics. ARIA attributes are enumerated
               (string "true"/"false"), not HTML boolean attributes, so
               we set the value explicitly when needed and omit the
               attribute entirely via Lit's nothing sentinel otherwise. -->
          <span class="entity-area" aria-hidden=${e.area?q:"true"}>
            ${e.area??q}
          </span>
          <span class="state-pill ${r}" aria-label="${e.name} state: ${a}">
            ${i?B`<ha-icon icon="mdi:alert-circle-outline" aria-hidden="true"></ha-icon>`:q}
            ${a}
          </span>
        </label>
        <button
          type="button"
          class="info-button"
          aria-label="More info for ${e.name}"
          title="More info"
          @click=${t=>this._openMoreInfo(e.entity_id,t)}
        >
          <ha-icon icon="mdi:information-outline"></ha-icon>
        </button>
      </div>
    `}_renderAlarmSelection(){if(0===this._alarms.length)return B`<div class="loading">No alarms available</div>`;const e=this._alarms.map(e=>({entity_id:e.entity_id,label:e.name.replace(/^Abode Alarm\s+/i,"")})).sort((e,t)=>e.label.localeCompare(t.label));return B`
      <div class="alarm-list" role="radiogroup" aria-label="Alarm to trigger">
        <label>
          <input
            type="radio"
            name="abode-action-alarm"
            value=""
            .checked=${0===this._selectedAlarms.length}
            @change=${()=>this._clearAlarmSelection()}
          />
          None (notification only)
        </label>
        ${e.map(e=>B`
            <label>
              <input
                type="radio"
                name="abode-action-alarm"
                value=${e.entity_id}
                .checked=${this._selectedAlarms.includes(e.entity_id)}
                @change=${()=>this._selectAlarm(e.entity_id)}
              />
              ${e.label}
            </label>
          `)}
      </div>
    `}};Xe.styles=s`
    :host {
      display: block;
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin-bottom: 8px;
    }

    .form-group input[type='text'] {
      width: 100%;
      padding: 12px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 14px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
      box-sizing: border-box;
    }

    .form-group input[type='text']:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
    }

    .form-group input[type='text'].error {
      border-color: var(--error-color, #f44336);
    }

    .error-text {
      display: block;
      color: var(--error-color, #f44336);
      font-size: 12px;
      margin-top: 4px;
    }

    .checkbox-group {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }

    .checkbox-group label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: normal;
      cursor: pointer;
    }

    .checkbox-group input[type='checkbox'] {
      width: 18px;
      height: 18px;
      cursor: pointer;
      accent-color: var(--primary-color, #03a9f4);
    }

    .delay-control {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .delay-control input[type='range'] {
      flex: 1;
      height: 4px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .delay-value {
      min-width: 50px;
      text-align: right;
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .sensor-search {
      width: 100%;
      padding: 8px 12px;
      margin-bottom: 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      font-size: 13px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
      box-sizing: border-box;
    }

    .sensor-search:focus {
      outline: none;
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
    }

    .sensor-categories {
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      padding: 12px;
    }

    .category {
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      padding-bottom: 12px;
    }

    .category:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }

    .category-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      text-transform: capitalize;
      margin-bottom: 8px;
      cursor: pointer;
    }

    .category-header > span {
      flex: 1;
    }

    .category-header input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .disclosure {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      font-size: 12px;
      line-height: 1;
      cursor: pointer;
      transition: transform 0.15s;
    }

    .disclosure[aria-expanded='true'] {
      transform: rotate(90deg);
    }

    .disclosure:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
      border-radius: 2px;
    }

    .category-items {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding-left: 24px;
    }

    .category-items label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: normal;
      cursor: pointer;
    }

    .category-items input[type='checkbox'] {
      width: 14px;
      height: 14px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .category-items .entity-area {
      font-size: 12px;
      color: var(--secondary-text-color, #757575);
    }

    /* Row layout: a flex row that puts the info button on the right
     * and the clickable label on the left. The label itself is a CSS
     * grid so name, area, and state pill align in columns across rows
     * like a table. Earlier we tried display:contents on the label to
     * make its children direct grid items of .sensor-row, but
     * Chromium's handling of display:contents on form controls is
     * inconsistent (the label loses its implicit click-forwarding to
     * the wrapped <input> under some conditions), which broke the
     * picker. The current shape is dumber and works.
     *
     * Column widths inside the label grid:
     *   checkbox    auto, minimal
     *   name        1fr,  takes remaining space and ellipsis-truncates
     *   area        minmax(0, auto), fits its content (collapses to 0
     *               on rows without an area so the state pill still
     *               aligns one column over)
     *   state pill  minmax(6.5rem, auto) — "unavailable" doesn't force
     *               ellipsis but a short "open" still column-aligns
     *               with longer labels in adjacent rows
     */
    .sensor-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sensor-row > label {
      flex: 1;
      min-width: 0;
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) minmax(0, auto) minmax(6.5rem, auto);
      align-items: center;
      column-gap: 12px;
      cursor: pointer;
    }

    .sensor-row.unavailable .entity-name {
      text-decoration: line-through;
      opacity: 0.7;
    }

    .entity-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
    }

    /* State pill — colored dot plus label. Pulls from HA's CSS variable
     * palette where available so it follows light/dark theming. The
     * leading "·" separator from the area column is dropped now that
     * the area sits in its own grid column. */
    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: var(--secondary-text-color, #757575);
      white-space: nowrap;
    }

    .state-pill::before {
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
    }

    .state-pill.on {
      color: var(--state-binary_sensor-active-color, var(--warning-color, #ff9800));
    }

    .state-pill.off {
      color: var(--state-binary_sensor-color, var(--success-color, #4caf50));
    }

    .state-pill.unavailable {
      color: var(--error-color, #f44336);
    }

    .state-pill.unavailable::before {
      /* Hide the dot for unavailable rows — the template renders an
       * <ha-icon> (mdi:alert-circle-outline) in its place. */
      display: none;
    }

    .state-pill.unavailable ha-icon {
      --mdc-icon-size: 14px;
    }

    .info-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      padding: 0;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      cursor: pointer;
      border-radius: 4px;
    }

    .info-button:hover {
      color: var(--primary-text-color);
      background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
    }

    .info-button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 1px;
    }

    .info-button ha-icon {
      --mdc-icon-size: 18px;
    }

    .category-header .unavailable-count {
      margin-left: 4px;
      font-size: 12px;
      font-weight: normal;
      color: var(--error-color, #f44336);
      text-transform: none;
    }

    /* Responsive grid: ~180px minimum per cell, so the panel auto-fits
     * 2-3 columns on a laptop and falls back to 1 on narrow viewports
     * without a media-query breakpoint. The row gap is tighter than the
     * column gap so columns read as paired up rather than as a single
     * wall of text. */
    /* Sits above the footer buttons and spans the full row so the warning
       reads before the Save button it is guarding. */
    .notify-only-confirm {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      flex: 1 1 100%;
      font-size: 13px;
      line-height: 1.4;
      color: var(--error-color, #db4437);
      background: var(--error-color, #db4437);
      background: color-mix(in srgb, var(--error-color, #db4437) 8%, transparent);
      border: 1px solid var(--error-color, #db4437);
      border-radius: 4px;
      padding: 8px 10px;
      margin-bottom: 8px;
    }

    .notify-only-confirm ha-icon {
      --mdc-icon-size: 18px;
      flex-shrink: 0;
    }

    .alarm-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px 16px;
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 4px;
      padding: 12px;
      max-height: 150px;
      overflow-y: auto;
    }

    .alarm-list label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: normal;
      cursor: pointer;
    }

    .alarm-list input[type='radio'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    /* Footer button styles — applied to <button slot="footer"> inside <abode-modal>.
     * The selector intentionally matches all slot="footer" buttons in this
     * shadow root, which today only exist inside <abode-modal>. */
    button[slot='footer'] {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    button[slot='footer'].cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    button[slot='footer'].cancel:hover {
      background: var(--secondary-background-color);
    }

    button[slot='footer'].primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    button[slot='footer'].primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    button[slot='footer'].primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    button[slot='footer']:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .loading {
      text-align: center;
      padding: 24px;
      color: var(--secondary-text-color);
    }

    .retry-row {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 32px 24px;
      text-align: center;
    }

    .retry-row .error-text {
      font-size: 14px;
      margin: 0;
    }

    .retry-row button {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      background: var(--primary-color, #03a9f4);
      color: white;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .retry-row button:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .retry-row button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: 2px;
    }
  `,e([pe({attribute:!1})],Xe.prototype,"hass",void 0),e([pe({attribute:!1})],Xe.prototype,"action",void 0),e([ue()],Xe.prototype,"_name",void 0),e([ue()],Xe.prototype,"_modes",void 0),e([ue()],Xe.prototype,"_delaySeconds",void 0),e([ue()],Xe.prototype,"_selectedSensors",void 0),e([ue()],Xe.prototype,"_selectedAlarms",void 0),e([ue()],Xe.prototype,"_sensors",void 0),e([ue()],Xe.prototype,"_alarms",void 0),e([ue()],Xe.prototype,"_errors",void 0),e([ue()],Xe.prototype,"_saving",void 0),e([ue()],Xe.prototype,"_loading",void 0),e([ue()],Xe.prototype,"_loadError",void 0),e([ue()],Xe.prototype,"_confirmNotificationOnly",void 0),e([ue()],Xe.prototype,"_expandedCategories",void 0),e([ue()],Xe.prototype,"_sensorSearch",void 0),Xe=e([ce("abode-action-editor")],Xe);let Ze=class extends ne{constructor(){super(...arguments),this._actions=[],this._loading=!0,this._error=null,this._editingAction=null,this._showEditor=!1,this._confirm=null,this._togglingIds=new Set,this._operationError=null,this._debugLogging=!1,this._copiedId=null,this._abort=null,this._copyResetTimeout=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}disconnectedCallback(){this._abort?.abort(),this._abort=null,null!==this._copyResetTimeout&&(clearTimeout(this._copyResetTimeout),this._copyResetTimeout=null),super.disconnectedCallback()}async _loadData(){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:t}=e;this._loading=!0,this._error=null;try{const e=await ge(this.hass);if(t.aborted)return;this._actions=e,async function(e){return e.callWS({type:"abode_security/config/get"})}(this.hass).then(e=>{t.aborted||(this._debugLogging=!0===e.debug_logging)}).catch(()=>{})}catch(e){if(t.aborted)return;this._error=e instanceof Error?e.message:"Failed to load actions"}finally{t.aborted||(this._loading=!1)}}async _copyActionId(e){try{await navigator.clipboard.writeText(e.id),this._copiedId=e.id,null!==this._copyResetTimeout&&clearTimeout(this._copyResetTimeout),this._copyResetTimeout=setTimeout(()=>{this._copyResetTimeout=null,this._copiedId===e.id&&(this._copiedId=null)},1500)}catch(e){console.error("Failed to copy action ID:",e),this._operationError="Failed to copy action ID"}}_getRecentTriggers(){return this._actions.filter(e=>e.last_triggered).sort((e,t)=>new Date(t.last_triggered).getTime()-new Date(e.last_triggered).getTime()).slice(0,5)}_formatTime(e){if(!e)return"";const t=new Date(e),o=(new Date).getTime()-t.getTime(),i=Math.floor(o/6e4),r=Math.floor(o/36e5),a=Math.floor(o/864e5);return i<1?"Just now":i<60?`${i}m ago`:r<24?`${r}h ago`:a<7?`${a}d ago`:t.toLocaleDateString()}_addAction(){this._editingAction=null,this._showEditor=!0}_editAction(e){this._editingAction=e,this._showEditor=!0}async _toggleAction(e){const t=e.id;this._togglingIds=new Set([...this._togglingIds,t]),this._operationError=null;try{const o=await ye(this.hass,t,{enabled:!e.enabled});this._actions=this._actions.map(e=>e.id===t?o:e)}catch(t){console.error("Failed to toggle action:",t),this._operationError=`Failed to ${e.enabled?"disable":"enable"} action`}finally{this._togglingIds=new Set([...this._togglingIds].filter(e=>e!==t))}}_requestDelete(e){this._confirm={kind:"delete",action:e}}async _confirmDelete(){if("delete"!==this._confirm?.kind)return;const{action:e}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(e,t){await e.callWS({type:"abode_security/actions/delete",action_id:t})}(this.hass,e.id),this._actions=this._actions.filter(t=>t.id!==e.id)}catch(e){console.error("Failed to delete action:",e),this._operationError="Failed to delete action"}}_requestTest(e){this._confirm={kind:"test",action:e}}async _confirmTest(){if("test"!==this._confirm?.kind)return;const{action:e}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(e,t){await e.callWS({type:"abode_security/actions/test",action_id:t})}(this.hass,e.id)}catch(e){console.error("Failed to test action:",e);const t=e?.message;this._operationError=t?`Failed to test action: ${t}`:"Failed to test action"}}_closeEditor(){this._showEditor=!1,this._editingAction=null}async _handleSave(){this._closeEditor(),await this._loadData()}render(){if(this._loading)return B`<div class="loading">Loading actions...</div>`;if(this._error)return B`<div class="error" role="alert">${this._error}</div>`;const e=this._getRecentTriggers();return B`
      ${this._operationError?B`
            <div class="operation-error" role="alert">
              ${this._operationError}
              <button
                class="dismiss-error"
                @click=${()=>this._operationError=null}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          `:""}

      <div class="actions-header">
        <button class="add-button" @click=${this._addAction} aria-label="Add new action">
          <ha-icon icon="mdi:plus"></ha-icon>
          Add Action
        </button>
      </div>

      ${0===this._actions.length?B`
            <div class="empty-state">
              <ha-icon icon="mdi:bell-off-outline"></ha-icon>
              <p>No actions configured</p>
              <button class="add-button" @click=${this._addAction}>
                <ha-icon icon="mdi:plus"></ha-icon>
                Create your first action
              </button>
            </div>
          `:B`
            <div class="actions-list" role="list">
              ${We(this._actions,e=>e.id,e=>this._renderActionRow(e))}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${0===e.length?B`<div class="empty-state" style="padding: 24px;">No recent triggers</div>`:B`
              <div class="trigger-list">
                ${e.map(e=>B`
                    <div class="trigger-item">
                      <span class="trigger-name">${e.name}</span>
                      <span class="trigger-time">${this._formatTime(e.last_triggered)}</span>
                    </div>
                  `)}
              </div>
            `}
      </div>

      ${this._showEditor?B`
            <abode-action-editor
              .hass=${this.hass}
              .action=${this._editingAction}
              @save=${this._handleSave}
              @cancel=${this._closeEditor}
            ></abode-action-editor>
          `:""}
      ${"delete"===this._confirm?.kind?this._renderDeleteDialog():""}
      ${"test"===this._confirm?.kind?this._renderTestDialog():""}
    `}_renderOutcomeBadge(e){if(!e.last_outcome||"armed"===e.last_outcome)return"";if("none"===e.last_outcome)return B`
        <span
          class="outcome-badge notification-only"
          title="This action only sends a notification. It does not raise an alarm or contact monitoring."
        >
          <ha-icon icon="mdi:bell-outline" aria-hidden="true"></ha-icon>
          notification only
        </span>
      `;const t="partial"===e.last_outcome;return B`
      <span
        class="outcome-badge failed"
        title=${t?"Some alarms failed to arm the last time this action fired. Monitoring may not have been contacted.":"The alarm did NOT fire the last time this action ran. Monitoring was not contacted. Check the alarm assigned to this action."}
      >
        <ha-icon icon="mdi:alert-octagon" aria-hidden="true"></ha-icon>
        ${t?"alarm partly failed":"alarm failed"}
      </span>
    `}_renderActionRow(e){const t=this._togglingIds.has(e.id),o=e.sensor_entity_ids.filter(e=>Ae(ke(this.hass,e))).length,i=e.sensor_entity_ids.length;return B`
      <div class="action-row ${e.enabled?"":"disabled"}" role="listitem">
        <div class="action-info">
          <div class="action-name">${e.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${e.modes.map(e=>B`<span class="mode-chip">${e}</span>`)}
            </div>
            ${o>0?B`
                  <span
                    class="stale-warning"
                    title=${1===o?"This sensor won't fire this action until it comes back online.":"These sensors won't fire this action until they come back online."}
                  >
                    <ha-icon icon="mdi:alert" aria-hidden="true"></ha-icon>
                    ${o} of ${i} ${1===i?"sensor":"sensors"}
                    unavailable
                  </span>
                `:""}
            ${this._renderOutcomeBadge(e)}
          </div>
        </div>
        <div class="action-controls">
          <label class="toggle-switch">
            <input
              type="checkbox"
              .checked=${e.enabled}
              .disabled=${t}
              @change=${()=>this._toggleAction(e)}
              aria-label="${e.enabled?"Disable":"Enable"} action"
            />
            <span class="toggle-slider"></span>
          </label>
          ${this._debugLogging?B`
                <button
                  class="icon-button"
                  @click=${()=>this._copyActionId(e)}
                  title=${this._copiedId===e.id?"Copied!":`Copy action ID (${e.id})`}
                  aria-label="Copy action ID"
                >
                  <ha-icon
                    icon=${this._copiedId===e.id?"mdi:check":"mdi:content-copy"}
                  ></ha-icon>
                </button>
              `:""}
          <button
            class="icon-button"
            @click=${()=>this._requestTest(e)}
            title="Test"
            aria-label="Test action"
          >
            <ha-icon icon="mdi:play"></ha-icon>
          </button>
          <button
            class="icon-button"
            @click=${()=>this._editAction(e)}
            title="Edit"
            aria-label="Edit action"
          >
            <ha-icon icon="mdi:pencil"></ha-icon>
          </button>
          <button
            class="icon-button delete"
            @click=${()=>this._requestDelete(e)}
            title="Delete"
            aria-label="Delete action"
          >
            <ha-icon icon="mdi:delete"></ha-icon>
          </button>
        </div>
      </div>
    `}_renderDeleteDialog(){return B`
      <abode-modal
        heading="Delete Action"
        variant="alertdialog"
        @dismiss=${()=>this._confirm=null}
      >
        <p>Delete action "${this._confirm?.action.name}"? This cannot be undone.</p>
        <button slot="footer" class="dialog-button cancel" @click=${()=>this._confirm=null}>
          Cancel
        </button>
        <button slot="footer" class="dialog-button danger" @click=${this._confirmDelete}>
          Delete
        </button>
      </abode-modal>
    `}_renderTestDialog(){return B`
      <abode-modal
        heading="Test Action"
        variant="alertdialog"
        @dismiss=${()=>this._confirm=null}
      >
        <p>
          This will trigger real alarms. Are you sure you want to test
          "${this._confirm?.action.name}"?
        </p>
        <button slot="footer" class="dialog-button cancel" @click=${()=>this._confirm=null}>
          Cancel
        </button>
        <button slot="footer" class="dialog-button primary" @click=${this._confirmTest}>
          Test
        </button>
      </abode-modal>
    `}};Ze.styles=s`
    :host {
      display: block;
    }

    .actions-header {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 16px;
    }

    .add-button {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: var(--primary-color, #03a9f4);
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .add-button:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    .add-button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .add-button ha-icon {
      --mdc-icon-size: 18px;
    }

    .actions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .action-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .action-row.disabled {
      opacity: 0.6;
    }

    .action-info {
      flex: 1;
      min-width: 0;
    }

    .action-name {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin-bottom: 4px;
    }

    .action-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .modes-list {
      display: flex;
      gap: 4px;
    }

    .mode-chip {
      padding: 2px 8px;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
    }

    /* Warning chip surfaced when a saved action references an entity
     * that is currently unavailable in hass.states — the trap that
     * caused the "Home Test" bug: UI looked fine but no event could
     * ever fire because the chosen sensors were offline. */
    .stale-warning {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--warning-color, #ff9800);
    }

    .stale-warning ha-icon {
      --mdc-icon-size: 16px;
    }

    .outcome-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
    }

    .outcome-badge ha-icon {
      --mdc-icon-size: 16px;
    }

    /* A security action that promised an alarm and didn't deliver is the
       loudest state this list can show — error red, not warning amber. */
    .outcome-badge.failed {
      color: var(--error-color, #db4437);
      font-weight: 500;
    }

    .outcome-badge.notification-only {
      color: var(--secondary-text-color, #727272);
    }

    .action-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .icon-button {
      width: 36px;
      height: 36px;
      padding: 0;
      border: none;
      background: transparent;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--secondary-text-color);
      transition:
        background 0.2s,
        color 0.2s;
    }

    .icon-button:hover {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--primary-text-color);
    }

    .icon-button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .icon-button.delete:hover {
      color: var(--error-color, #f44336);
    }

    .icon-button ha-icon {
      --mdc-icon-size: 20px;
    }

    .empty-state {
      text-align: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .empty-state ha-icon {
      --mdc-icon-size: 48px;
      margin-bottom: 16px;
      opacity: 0.5;
    }

    .empty-state p {
      margin: 0 0 16px 0;
      font-size: 16px;
    }

    .recent-triggers {
      margin-top: 32px;
    }

    .recent-triggers h3 {
      font-size: 16px;
      font-weight: 500;
      color: var(--primary-text-color);
      margin: 0 0 12px 0;
    }

    .trigger-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .trigger-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }

    .trigger-name {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    .trigger-time {
      font-size: 12px;
      color: var(--secondary-text-color);
    }

    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .error {
      padding: 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
    }

    .operation-error {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background-color: var(--error-color, #f44336);
      color: white;
      border-radius: 4px;
      margin-bottom: 16px;
    }

    .dismiss-error {
      background: transparent;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
      opacity: 0.8;
    }

    .dismiss-error:hover {
      opacity: 1;
    }

    /* Dialog button styles — applied to <button slot="footer"> inside <abode-modal>. */
    .dialog-button {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .dialog-button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .dialog-button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .dialog-button.danger {
      background: var(--error-color, #f44336);
      color: white;
    }

    .dialog-button.danger:hover {
      background: #d32f2f;
    }

    .dialog-button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .dialog-button.primary:hover {
      background: var(--primary-color-dark, #0288d1);
    }

    /* Toggle switch */
    .toggle-switch {
      position: relative;
      width: 40px;
      height: 20px;
    }

    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: 0.3s;
      border-radius: 20px;
    }

    .toggle-slider:before {
      position: absolute;
      content: '';
      height: 16px;
      width: 16px;
      left: 2px;
      bottom: 2px;
      background-color: white;
      transition: 0.3s;
      border-radius: 50%;
    }

    .toggle-switch input:checked + .toggle-slider {
      background-color: var(--primary-color, #03a9f4);
    }

    .toggle-switch input:checked + .toggle-slider:before {
      transform: translateX(20px);
    }

    .toggle-switch input:disabled + .toggle-slider {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .toggle-switch input:focus-visible + .toggle-slider {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
  `,e([pe({attribute:!1})],Ze.prototype,"hass",void 0),e([ue()],Ze.prototype,"_actions",void 0),e([ue()],Ze.prototype,"_loading",void 0),e([ue()],Ze.prototype,"_error",void 0),e([ue()],Ze.prototype,"_editingAction",void 0),e([ue()],Ze.prototype,"_showEditor",void 0),e([ue()],Ze.prototype,"_confirm",void 0),e([ue()],Ze.prototype,"_togglingIds",void 0),e([ue()],Ze.prototype,"_operationError",void 0),e([ue()],Ze.prototype,"_debugLogging",void 0),e([ue()],Ze.prototype,"_copiedId",void 0),Ze=e([ce("abode-actions-tab")],Ze);let Qe=class extends ne{constructor(){super(...arguments),this.selectedCameraEntityId=null,this._cameras=[],this._loading=!0,this._error=null,this._unauthorized=!1,this._abort=null,this._highlightTimeout=null,this._autoOpenedFor=null}connectedCallback(){super.connectedCallback(),this._loadCameras()}disconnectedCallback(){this._abort?.abort(),this._abort=null,null!==this._highlightTimeout&&(clearTimeout(this._highlightTimeout),this._highlightTimeout=null),super.disconnectedCallback()}updated(e){e.has("selectedCameraEntityId")&&(this._autoOpenedFor=null);(e.has("selectedCameraEntityId")||e.has("_cameras"))&&this.selectedCameraEntityId&&(this._scrollToSelected(),this._maybeAutoOpenMoreInfo())}async _loadCameras(){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:t}=e;this._loading=!0,this._error=null,this._unauthorized=!1;try{const e=await async function(e){return(await e.callWS({type:"abode_security/entities/cameras"})).cameras}(this.hass);if(t.aborted)return;this._cameras=e}catch(e){if(t.aborted)return;null!==e&&"object"==typeof e&&"code"in e&&"unauthorized"===e.code?this._unauthorized=!0:this._error=e instanceof Error?e.message:"Failed to load cameras"}finally{t.aborted||(this._loading=!1)}}_scrollToSelected(){requestAnimationFrame(()=>{if(!this.selectedCameraEntityId)return;const e=this.shadowRoot?.querySelector(`[data-entity-id="${CSS.escape(this.selectedCameraEntityId)}"]`);e&&(e.scrollIntoView({behavior:"smooth",block:"nearest"}),e.classList.add("highlight"),null!==this._highlightTimeout&&clearTimeout(this._highlightTimeout),this._highlightTimeout=setTimeout(()=>{e.classList.remove("highlight"),this._highlightTimeout=null},1500))})}_maybeAutoOpenMoreInfo(){const e=this.selectedCameraEntityId;e&&this._autoOpenedFor!==e&&this._cameras.some(t=>t.entity_id===e)&&(this._autoOpenedFor=e,this._openMoreInfo(e))}_openMoreInfo(e){this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:e},bubbles:!0,composed:!0}))}render(){return this._loading?B`<div class="loading">Loading cameras…</div>`:this._unauthorized?B`
        <div class="empty-state">Admin permissions are required to view the Cameras tab.</div>
      `:this._error?B`
        <div class="error">
          ${this._error}
          <div>
            <button class="retry-button" @click=${()=>this._loadCameras()}>Retry</button>
          </div>
        </div>
      `:0===this._cameras.length?B`<div class="empty-state">No cameras found in Home Assistant.</div>`:B`
      <div class="camera-list">${this._cameras.map(e=>this._renderCard(e))}</div>
    `}_renderCard(e){const t=this.hass.states?.[e.entity_id];return B`
      <div
        class="camera-card"
        data-entity-id=${e.entity_id}
        role="button"
        tabindex="0"
        @click=${()=>this._openMoreInfo(e.entity_id)}
        @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._openMoreInfo(e.entity_id))}}
      >
        <div class="camera-card-header">
          <span class="camera-name">${e.name}</span>
          ${e.area?B`<span class="area-chip">${e.area}</span>`:""}
        </div>
        <ha-camera-stream
          class="camera-stream"
          allow-exoplayer
          muted
          .hass=${this.hass}
          .stateObj=${t}
        ></ha-camera-stream>
      </div>
    `}};var Ye;Qe.styles=s`
    :host {
      display: block;
    }

    .loading,
    .empty-state {
      padding: 32px 16px;
      text-align: center;
      color: var(--secondary-text-color, #757575);
    }

    .error {
      padding: 16px;
      color: var(--error-color, #db4437);
    }

    .retry-button {
      margin-top: 8px;
      padding: 8px 16px;
      border: 1px solid var(--primary-color, #03a9f4);
      background: transparent;
      color: var(--primary-color, #03a9f4);
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }

    .camera-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .camera-card {
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      overflow: hidden;
      background: var(--card-background-color, #fff);
      cursor: pointer;
      transition: box-shadow 0.2s;
    }

    .camera-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .camera-card.highlight {
      animation: highlight-pulse 1.5s ease-out;
    }

    @keyframes highlight-pulse {
      0% {
        box-shadow: 0 0 0 4px var(--primary-color, #03a9f4);
      }
      100% {
        box-shadow: 0 0 0 0 transparent;
      }
    }

    .camera-card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
    }

    .camera-name {
      font-weight: 500;
      flex: 1;
    }

    .area-chip {
      font-size: 11px;
      padding: 2px 8px;
      background: var(--secondary-background-color, #f5f5f5);
      border-radius: 12px;
      color: var(--secondary-text-color, #757575);
    }

    .camera-stream {
      display: block;
      width: 100%;
      min-height: 160px;
      background: #000;
    }
  `,e([pe({attribute:!1})],Qe.prototype,"hass",void 0),e([pe({attribute:!1})],Qe.prototype,"selectedCameraEntityId",void 0),e([ue()],Qe.prototype,"_cameras",void 0),e([ue()],Qe.prototype,"_loading",void 0),e([ue()],Qe.prototype,"_error",void 0),e([ue()],Qe.prototype,"_unauthorized",void 0),Qe=e([ce("abode-cameras-tab")],Qe);let et=Ye=class extends ne{constructor(){super(...arguments),this._activeTab=Ye._initialTabFromUrl(),this._initialCameraSelection=Ye._initialCameraFromUrl()}static _initialTabFromUrl(){const e=new URLSearchParams(window.location.search).get("tab");return"cameras"===e||"actions"===e?e:"modes"}static _initialCameraFromUrl(){return new URLSearchParams(window.location.search).get("camera")}connectedCallback(){super.connectedCallback(),this._activeTab=Ye._initialTabFromUrl(),this._initialCameraSelection=Ye._initialCameraFromUrl()}_switchTab(e){"cameras"===this._activeTab&&"cameras"!==e&&(this._initialCameraSelection=null),this._activeTab=e}render(){const e="modes"===this._activeTab?"modes-panel":"actions"===this._activeTab?"actions-panel":"cameras-panel",t="modes"===this._activeTab?"modes-tab":"actions"===this._activeTab?"actions-tab":"cameras-tab";return B`
      <div class="panel-content">
        <div class="header">
          <h1>Abode Configuration</h1>
        </div>

        <div class="tab-bar" role="tablist">
          <button
            role="tab"
            id="modes-tab"
            aria-selected=${"modes"===this._activeTab}
            aria-controls="modes-panel"
            class=${"modes"===this._activeTab?"active":""}
            @click=${()=>this._switchTab("modes")}
          >
            Modes
          </button>
          <button
            role="tab"
            id="actions-tab"
            aria-selected=${"actions"===this._activeTab}
            aria-controls="actions-panel"
            class=${"actions"===this._activeTab?"active":""}
            @click=${()=>this._switchTab("actions")}
          >
            Actions
          </button>
          <button
            role="tab"
            id="cameras-tab"
            aria-selected=${"cameras"===this._activeTab}
            aria-controls="cameras-panel"
            class=${"cameras"===this._activeTab?"active":""}
            @click=${()=>this._switchTab("cameras")}
          >
            Cameras
          </button>
        </div>

        <div
          class="tab-content"
          role="tabpanel"
          id=${e}
          aria-labelledby=${t}
        >
          ${"modes"===this._activeTab?B`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`:"actions"===this._activeTab?B`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`:B`<abode-cameras-tab
                  .hass=${this.hass}
                  .selectedCameraEntityId=${this._initialCameraSelection}
                ></abode-cameras-tab>`}
        </div>
      </div>
    `}};et.styles=s`
    :host {
      display: block;
      background-color: var(--primary-background-color);
      color: var(--primary-text-color);
      min-height: 100vh;
    }

    .panel-content {
      max-width: 1200px;
      margin: 0 auto;
      padding: 16px;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }

    h1 {
      font-size: 24px;
      font-weight: 400;
      margin: 0;
      color: var(--primary-text-color);
    }

    .tab-bar {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      margin-bottom: 16px;
    }

    .tab-bar button {
      padding: 12px 24px;
      border: none;
      background: transparent;
      color: var(--secondary-text-color, #757575);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition:
        color 0.2s,
        border-color 0.2s;
    }

    .tab-bar button:hover {
      color: var(--primary-text-color);
    }

    .tab-bar button.active {
      color: var(--primary-color, #03a9f4);
      border-bottom-color: var(--primary-color, #03a9f4);
    }

    .tab-bar button:focus {
      outline: none;
    }

    .tab-bar button:focus-visible {
      outline: 2px solid var(--primary-color, #03a9f4);
      outline-offset: -2px;
    }

    .tab-content {
      min-height: 400px;
    }
  `,e([pe({attribute:!1})],et.prototype,"hass",void 0),e([ue()],et.prototype,"_activeTab",void 0),e([ue()],et.prototype,"_initialCameraSelection",void 0),et=Ye=e([ce("abode-configuration-panel")],et);export{et as AbodeConfigurationPanel};
