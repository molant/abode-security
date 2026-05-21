function t(t,e,o,i){var r,s=arguments.length,n=s<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(t,e,o,i);else for(var a=t.length-1;a>=0;a--)(r=t[a])&&(n=(s<3?r(n):s>3?r(e,o,n):r(e,o))||n);return s>3&&n&&Object.defineProperty(e,o,n),n}"function"==typeof SuppressedError&&SuppressedError;const e=globalThis,o=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),r=new WeakMap;let s=class{constructor(t,e,o){if(this._$cssResult$=!0,o!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(o&&void 0===t){const o=void 0!==e&&1===e.length;o&&(t=r.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),o&&r.set(e,t))}return t}toString(){return this.cssText}};const n=(t,...e)=>{const o=1===t.length?t[0]:e.reduce((e,o,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[i+1],t[0]);return new s(o,t,i)},a=o?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const o of t.cssRules)e+=o.cssText;return(t=>new s("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,g=globalThis,m=g.trustedTypes,b=m?m.emptyScript:"",f=g.reactiveElementPolyfillSupport,_=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?b:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=null!==t;break;case Number:o=null===t?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch(t){o=null}}return o}},v=(t,e)=>!l(t,e),x={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=x){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const o=Symbol(),i=this.getPropertyDescriptor(t,o,e);void 0!==i&&c(this.prototype,t,i)}}static getPropertyDescriptor(t,e,o){const{get:i,set:r}=d(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const s=i?.call(this);r?.call(this,e),this.requestUpdate(t,s,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??x}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const o of e)this.createProperty(o,t[o])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,o]of e)this.elementProperties.set(t,o)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const o=this._$Eu(t,e);void 0!==o&&this._$Eh.set(o,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const o=new Set(t.flat(1/0).reverse());for(const t of o)e.unshift(a(t))}else void 0!==t&&e.push(a(t));return e}static _$Eu(t,e){const o=e.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const o of e.keys())this.hasOwnProperty(o)&&(t.set(o,this[o]),delete this[o]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(o)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const o of i){const i=document.createElement("style"),r=e.litNonce;void 0!==r&&i.setAttribute("nonce",r),i.textContent=o.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$ET(t,e){const o=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,o);if(void 0!==i&&!0===o.reflect){const r=(void 0!==o.converter?.toAttribute?o.converter:y).toAttribute(e,o.type);this._$Em=t,null==r?this.removeAttribute(i):this.setAttribute(i,r),this._$Em=null}}_$AK(t,e){const o=this.constructor,i=o._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=o.getPropertyOptions(i),r="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=i;const s=r.fromAttribute(e,t.type);this[i]=s??this._$Ej?.get(i)??s,this._$Em=null}}requestUpdate(t,e,o,i=!1,r){if(void 0!==t){const s=this.constructor;if(!1===i&&(r=this[t]),o??=s.getPropertyOptions(t),!((o.hasChanged??v)(r,e)||o.useDefault&&o.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(s._$Eu(t,o))))return;this.C(t,e,o)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:o,reflect:i,wrapped:r},s){o&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,s??e??this[t]),!0!==r||void 0!==s)||(this._$AL.has(t)||(this.hasUpdated||o||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,o]of t){const{wrapped:t}=o,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,o,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[_("elementProperties")]=new Map,$[_("finalized")]=new Map,f?.({ReactiveElement:$}),(g.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,A=t=>t,k=w.trustedTypes,S=k?k.createPolicy("lit-html",{createHTML:t=>t}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,M=`<${T}>`,z=document,P=()=>z.createComment(""),O=t=>null===t||"object"!=typeof t&&"function"!=typeof t,D=Array.isArray,U="[ \t\n\f\r]",R=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,F=/-->/g,N=/>/g,H=RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),I=/'/g,j=/"/g,L=/^(?:script|style|textarea|title)$/i,B=(t=>(e,...o)=>({_$litType$:t,strings:e,values:o}))(1),q=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),V=new WeakMap,K=z.createTreeWalker(z,129);function J(t,e){if(!D(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(e):e}class X{constructor({strings:t,_$litType$:e},o){let i;this.parts=[];let r=0,s=0;const n=t.length-1,a=this.parts,[l,c]=((t,e)=>{const o=t.length-1,i=[];let r,s=2===e?"<svg>":3===e?"<math>":"",n=R;for(let e=0;e<o;e++){const o=t[e];let a,l,c=-1,d=0;for(;d<o.length&&(n.lastIndex=d,l=n.exec(o),null!==l);)d=n.lastIndex,n===R?"!--"===l[1]?n=F:void 0!==l[1]?n=N:void 0!==l[2]?(L.test(l[2])&&(r=RegExp("</"+l[2],"g")),n=H):void 0!==l[3]&&(n=H):n===H?">"===l[0]?(n=r??R,c=-1):void 0===l[1]?c=-2:(c=n.lastIndex-l[2].length,a=l[1],n=void 0===l[3]?H:'"'===l[3]?j:I):n===j||n===I?n=H:n===F||n===N?n=R:(n=H,r=void 0);const h=n===H&&t[e+1].startsWith("/>")?" ":"";s+=n===R?o+M:c>=0?(i.push(a),o.slice(0,c)+E+o.slice(c)+C+h):o+C+(-2===c?e:h)}return[J(t,s+(t[o]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]})(t,e);if(this.el=X.createElement(l,o),K.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=K.nextNode())&&a.length<n;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(E)){const e=c[s++],o=i.getAttribute(t).split(C),n=/([.?@])?(.*)/.exec(e);a.push({type:1,index:r,name:n[2],strings:o,ctor:"."===n[1]?tt:"?"===n[1]?et:"@"===n[1]?ot:Y}),i.removeAttribute(t)}else t.startsWith(C)&&(a.push({type:6,index:r}),i.removeAttribute(t));if(L.test(i.tagName)){const t=i.textContent.split(C),e=t.length-1;if(e>0){i.textContent=k?k.emptyScript:"";for(let o=0;o<e;o++)i.append(t[o],P()),K.nextNode(),a.push({type:2,index:++r});i.append(t[e],P())}}}else if(8===i.nodeType)if(i.data===T)a.push({type:2,index:r});else{let t=-1;for(;-1!==(t=i.data.indexOf(C,t+1));)a.push({type:7,index:r}),t+=C.length-1}r++}}static createElement(t,e){const o=z.createElement("template");return o.innerHTML=t,o}}function Z(t,e,o=t,i){if(e===q)return e;let r=void 0!==i?o._$Co?.[i]:o._$Cl;const s=O(e)?void 0:e._$litDirective$;return r?.constructor!==s&&(r?._$AO?.(!1),void 0===s?r=void 0:(r=new s(t),r._$AT(t,o,i)),void 0!==i?(o._$Co??=[])[i]=r:o._$Cl=r),void 0!==r&&(e=Z(t,r._$AS(t,e.values),r,i)),e}class G{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:o}=this._$AD,i=(t?.creationScope??z).importNode(e,!0);K.currentNode=i;let r=K.nextNode(),s=0,n=0,a=o[0];for(;void 0!==a;){if(s===a.index){let e;2===a.type?e=new Q(r,r.nextSibling,this,t):1===a.type?e=new a.ctor(r,a.name,a.strings,this,t):6===a.type&&(e=new it(r,this,t)),this._$AV.push(e),a=o[++n]}s!==a?.index&&(r=K.nextNode(),s++)}return K.currentNode=z,i}p(t){let e=0;for(const o of this._$AV)void 0!==o&&(void 0!==o.strings?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,o,i){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Z(this,t,e),O(t)?t===W||null==t||""===t?(this._$AH!==W&&this._$AR(),this._$AH=W):t!==this._$AH&&t!==q&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>D(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==W&&O(this._$AH)?this._$AA.nextSibling.data=t:this.T(z.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:o}=t,i="number"==typeof o?this._$AC(t):(void 0===o.el&&(o.el=X.createElement(J(o.h,o.h[0]),this.options)),o);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new G(i,this),o=t.u(this.options);t.p(e),this.T(o),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new X(t)),e}k(t){D(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let o,i=0;for(const r of t)i===e.length?e.push(o=new Q(this.O(P()),this.O(P()),this,this.options)):o=e[i],o._$AI(r),i++;i<e.length&&(this._$AR(o&&o._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=A(t).nextSibling;A(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class Y{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,o,i,r){this.type=1,this._$AH=W,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=r,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=W}_$AI(t,e=this,o,i){const r=this.strings;let s=!1;if(void 0===r)t=Z(this,t,e,0),s=!O(t)||t!==this._$AH&&t!==q,s&&(this._$AH=t);else{const i=t;let n,a;for(t=r[0],n=0;n<r.length-1;n++)a=Z(this,i[o+n],e,n),a===q&&(a=this._$AH[n]),s||=!O(a)||a!==this._$AH[n],a===W?t=W:t!==W&&(t+=(a??"")+r[n+1]),this._$AH[n]=a}s&&!i&&this.j(t)}j(t){t===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class tt extends Y{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===W?void 0:t}}class et extends Y{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==W)}}class ot extends Y{constructor(t,e,o,i,r){super(t,e,o,i,r),this.type=5}_$AI(t,e=this){if((t=Z(this,t,e,0)??W)===q)return;const o=this._$AH,i=t===W&&o!==W||t.capture!==o.capture||t.once!==o.once||t.passive!==o.passive,r=t!==W&&(o===W||i);i&&this.element.removeEventListener(this.name,this,o),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class it{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){Z(this,t)}}const rt={I:Q},st=w.litHtmlPolyfillSupport;st?.(X,Q),(w.litHtmlVersions??=[]).push("3.3.2");const nt=globalThis;let at=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,o)=>{const i=o?.renderBefore??e;let r=i._$litPart$;if(void 0===r){const t=o?.renderBefore??null;i._$litPart$=r=new Q(e.insertBefore(P(),t),t,void 0,o??{})}return r._$AI(t),r})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}};at._$litElement$=!0,at.finalized=!0,nt.litElementHydrateSupport?.({LitElement:at});const lt=nt.litElementPolyfillSupport;lt?.({LitElement:at}),(nt.litElementVersions??=[]).push("4.2.2");const ct=t=>(e,o)=>{void 0!==o?o.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},dt={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},ht=(t=dt,e,o)=>{const{kind:i,metadata:r}=o;let s=globalThis.litPropertyMetadata.get(r);if(void 0===s&&globalThis.litPropertyMetadata.set(r,s=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),s.set(o.name,t),"accessor"===i){const{name:i}=o;return{set(o){const r=e.get.call(this);e.set.call(this,o),this.requestUpdate(i,r,t,!0,o)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=o;return function(o){const r=this[i];e.call(this,o),this.requestUpdate(i,r,t,!0,o)}}throw Error("Unsupported decorator location: "+i)};function pt(t){return(e,o)=>"object"==typeof o?ht(t,e,o):((t,e,o)=>{const i=e.hasOwnProperty(o);return e.constructor.createProperty(o,t),i?Object.getOwnPropertyDescriptor(e,o):void 0})(t,e,o)}function ut(t){return pt({...t,state:!0,attribute:!1})}async function gt(t){return(await t.callWS({type:"abode_security/actions/list"})).actions}async function mt(t){return(await t.callWS({type:"abode_security/modes/list"})).modes}async function bt(t){return(await t.callWS({type:"abode_security/entities/sensors"})).sensors}async function ft(t){return(await t.callWS({type:"abode_security/entities/alarms"})).alarms}async function _t(t,e,o){return t.callWS({type:"abode_security/actions/update",action_id:e,...o})}let yt=0;const vt=[],xt=["a[href]","button:not([disabled])",'input:not([disabled]):not([type="hidden"])',"textarea:not([disabled])","select:not([disabled])",'[tabindex]:not([tabindex="-1"])'].join(",");let $t=class extends at{constructor(){super(...arguments),this.heading="",this.variant="dialog",this.size="sm",this.dismissOnOverlay=!0,this.dismissOnEscape=!0,this._hasFooterContent=!1,this._headingId="abode-modal-heading-"+ ++yt,this._previouslyFocused=null,this._onOverlayClick=t=>{this.dismissOnOverlay&&t.target===t.currentTarget&&this._dismiss()},this._onDocKeydown=t=>{this.dismissOnEscape&&vt[vt.length-1]===this&&"Escape"===t.key&&this._dismiss()},this._onFooterSlotChange=t=>{const e=t.target;this._hasFooterContent=e.assignedElements().length>0},this._onSentinelStartFocus=()=>{this._redirectFocus("last")},this._onSentinelEndFocus=()=>{this._redirectFocus("first")}}_redirectFocus(t){const e=this._getFocusable();if(0===e.length)return void this._focusBox();("first"===t?e[0]:e[e.length-1]).focus()}_getFocusable(){const t=this.shadowRoot?.querySelectorAll('slot:not([name]), slot[name="footer"]');if(!t)return[];const e=[];for(const o of t)for(const t of o.assignedElements({flatten:!0}))t instanceof HTMLElement&&(t.matches(xt)&&e.push(t),e.push(...t.querySelectorAll(xt)));return e.filter(t=>t.tabIndex>=0)}_focusBox(){const t=this.shadowRoot?.querySelector(".modal-box");t?.focus()}_dismiss(){this.dispatchEvent(new CustomEvent("dismiss",{bubbles:!0,composed:!0}))}connectedCallback(){super.connectedCallback(),null===this._previouslyFocused&&(this._previouslyFocused=document.activeElement),vt.push(this),document.addEventListener("keydown",this._onDocKeydown)}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this._onDocKeydown);const t=vt.indexOf(this);-1!==t&&vt.splice(t,1);const e=document.activeElement;(!e||e===document.body||this.contains(e))&&this._previouslyFocused?.focus?.(),this._previouslyFocused=null}firstUpdated(){const t=this._getFocusable();t.length>0?t[0].focus():this._focusBox()}render(){return B`
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
    `}};$t.styles=n`
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
  `,t([pt({type:String})],$t.prototype,"heading",void 0),t([pt({type:String})],$t.prototype,"variant",void 0),t([pt({type:String})],$t.prototype,"size",void 0),t([pt({type:Boolean,attribute:"dismiss-on-overlay"})],$t.prototype,"dismissOnOverlay",void 0),t([pt({type:Boolean,attribute:"dismiss-on-escape"})],$t.prototype,"dismissOnEscape",void 0),t([ut()],$t.prototype,"_hasFooterContent",void 0),$t=t([ct("abode-modal")],$t);let wt=class extends at{constructor(){super(...arguments),this._modes=[],this._actions=[],this._loading=!0,this._error=null,this._confirmMode=null,this._settingModeId=null,this._setError=null,this._abort=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}disconnectedCallback(){this._abort?.abort(),this._abort=null,super.disconnectedCallback()}async _loadData(t={}){this._abort?.abort();const e=new AbortController;this._abort=e;const{signal:o}=e;t.silent||(this._loading=!0),this._error=null;try{const[t,e]=await Promise.all([mt(this.hass),gt(this.hass)]);if(o.aborted)return;this._modes=t,this._actions=e}catch(t){if(o.aborted)return;this._error=t instanceof Error?t.message:"Failed to load data"}finally{o.aborted||t.silent||(this._loading=!1)}}_getActionsForMode(t){return this._actions.filter(e=>e.enabled&&e.modes.includes(t))}_requestSwitch(t){t.active||null!==this._settingModeId||(this._setError=null,this._confirmMode=t)}async _confirmSwitch(){if(!this._confirmMode)return;const t=this._confirmMode;this._confirmMode=null,this._settingModeId=t.id,this._setError=null;try{await async function(t,e){await t.callWS({type:"abode_security/modes/set",mode_id:e})}(this.hass,t.id)}catch(t){return console.error("Failed to set mode:",t),this._setError="Failed to change mode",void(this._settingModeId=null)}await this._loadData({silent:!0}),this._error&&(this._setError=`Mode changed; refresh failed: ${this._error}`,this._error=null),this._settingModeId=null}render(){return this._loading?B`<div class="loading">Loading modes...</div>`:this._error?B`<div class="error" role="alert">${this._error}</div>`:B`
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

      <div class="modes-grid">${this._modes.map(t=>this._renderModeCard(t))}</div>

      ${this._confirmMode?this._renderConfirmDialog(this._confirmMode):""}
    `}_renderConfirmDialog(t){return B`
      <abode-modal
        heading="Switch mode?"
        variant="alertdialog"
        @dismiss=${()=>this._confirmMode=null}
      >
        <p>
          Switch the system to <strong>${t.name}</strong>? This changes the live arming state
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
    `}_renderModeCard(t){const e=this._getActionsForMode(t.id),o=this._settingModeId===t.id,i=null!==this._settingModeId;return B`
      <div class="mode-card ${t.active?"active":""}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${t.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${t.name}</h3>
            <div class="badges">
              <span class="badge"
                >${t.action_count} ${1===t.action_count?"action":"actions"}</span
              >
              ${t.active?B`<span class="badge active">Active</span>`:""}
            </div>
          </div>
        </div>

        ${e.length>0?B`
              <ul class="action-list" aria-label="Actions for ${t.name} mode">
                ${e.map(t=>B`
                    <li>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${t.name}
                    </li>
                  `)}
              </ul>
            `:B`<div class="empty-actions">No actions configured</div>`}
        ${t.active?B`<div class="current-mode-label">Current mode</div>`:B`
              <button
                class="switch-button"
                ?disabled=${i}
                aria-label=${`Switch to ${t.name} mode`}
                @click=${()=>this._requestSwitch(t)}
              >
                ${o?"Switching…":`Switch to ${t.name}`}
              </button>
            `}
      </div>
    `}};wt.styles=n`
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
  `,t([pt({attribute:!1})],wt.prototype,"hass",void 0),t([ut()],wt.prototype,"_modes",void 0),t([ut()],wt.prototype,"_actions",void 0),t([ut()],wt.prototype,"_loading",void 0),t([ut()],wt.prototype,"_error",void 0),t([ut()],wt.prototype,"_confirmMode",void 0),t([ut()],wt.prototype,"_settingModeId",void 0),t([ut()],wt.prototype,"_setError",void 0),wt=t([ct("abode-modes-tab")],wt);const At=2;let kt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,o){this._$Ct=t,this._$AM=e,this._$Ci=o}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};const{I:St}=rt,Et=t=>t,Ct=()=>document.createComment(""),Tt=(t,e,o)=>{const i=t._$AA.parentNode,r=void 0===e?t._$AB:e._$AA;if(void 0===o){const e=i.insertBefore(Ct(),r),s=i.insertBefore(Ct(),r);o=new St(e,s,t,t.options)}else{const e=o._$AB.nextSibling,s=o._$AM,n=s!==t;if(n){let e;o._$AQ?.(t),o._$AM=t,void 0!==o._$AP&&(e=t._$AU)!==s._$AU&&o._$AP(e)}if(e!==r||n){let t=o._$AA;for(;t!==e;){const e=Et(t).nextSibling;Et(i).insertBefore(t,r),t=e}}}return o},Mt=(t,e,o=t)=>(t._$AI(e,o),t),zt={},Pt=(t,e=zt)=>t._$AH=e,Ot=t=>{t._$AR(),t._$AA.remove()},Dt=(t,e,o)=>{const i=new Map;for(let r=e;r<=o;r++)i.set(t[r],r);return i},Ut=(t=>(...e)=>({_$litDirective$:t,values:e}))(class extends kt{constructor(t){if(super(t),t.type!==At)throw Error("repeat() can only be used in text expressions")}dt(t,e,o){let i;void 0===o?o=e:void 0!==e&&(i=e);const r=[],s=[];let n=0;for(const e of t)r[n]=i?i(e,n):n,s[n]=o(e,n),n++;return{values:s,keys:r}}render(t,e,o){return this.dt(t,e,o).values}update(t,[e,o,i]){const r=(t=>t._$AH)(t),{values:s,keys:n}=this.dt(e,o,i);if(!Array.isArray(r))return this.ut=n,s;const a=this.ut??=[],l=[];let c,d,h=0,p=r.length-1,u=0,g=s.length-1;for(;h<=p&&u<=g;)if(null===r[h])h++;else if(null===r[p])p--;else if(a[h]===n[u])l[u]=Mt(r[h],s[u]),h++,u++;else if(a[p]===n[g])l[g]=Mt(r[p],s[g]),p--,g--;else if(a[h]===n[g])l[g]=Mt(r[h],s[g]),Tt(t,l[g+1],r[h]),h++,g--;else if(a[p]===n[u])l[u]=Mt(r[p],s[u]),Tt(t,r[h],r[p]),p--,u++;else if(void 0===c&&(c=Dt(n,u,g),d=Dt(a,h,p)),c.has(a[h]))if(c.has(a[p])){const e=d.get(n[u]),o=void 0!==e?r[e]:null;if(null===o){const e=Tt(t,r[h]);Mt(e,s[u]),l[u]=e}else l[u]=Mt(o,s[u]),Tt(t,r[h],o),r[e]=null;u++}else Ot(r[p]),p--;else Ot(r[h]),h++;for(;u<=g;){const e=Tt(t,l[g+1]);Mt(e,s[u]),l[u++]=e}for(;h<=p;){const t=r[h++];null!==t&&Ot(t)}return this.ut=n,Pt(t,l),q}});function Rt(t,e,o="unavailable"){return t.states?.[e]?.state??o}function Ft(t){return"unavailable"===t||"unknown"===t}const Nt=["standby","home","away"];function Ht(t,e){return t.includes(e)?t.filter(t=>t!==e):[...t,e]}const It=new Map(["door","window","motion","smoke","gas","carbon_monoxide","moisture"].map((t,e)=>[t,e]));function jt(t,e){return(It.get(t)??Number.MAX_SAFE_INTEGER)-(It.get(e)??Number.MAX_SAFE_INTEGER)||t.localeCompare(e)}const Lt={door:{on:"open",off:"closed"},window:{on:"open",off:"closed"},garage_door:{on:"open",off:"closed"},opening:{on:"open",off:"closed"},motion:{on:"detected",off:"clear"},occupancy:{on:"detected",off:"clear"},presence:{on:"detected",off:"clear"},moisture:{on:"wet",off:"dry"},smoke:{on:"detected",off:"clear"},gas:{on:"detected",off:"clear"},carbon_monoxide:{on:"detected",off:"clear"}};let Bt=class extends at{constructor(){super(...arguments),this.action=null,this._name="",this._modes=[],this._delaySeconds=0,this._selectedSensors=[],this._selectedAlarms=[],this._sensors=null,this._alarms=[],this._errors={},this._saving=!1,this._loading=!0,this._loadError=null,this._expandedCategories=new Set,this._sensorSearch="",this._abort=null}async connectedCallback(){super.connectedCallback(),this.action&&this._populateForm(),await this._loadEntities()}disconnectedCallback(){this._abort?.abort(),this._abort=null,super.disconnectedCallback()}async _loadEntities(){this._abort?.abort();const t=new AbortController;this._abort=t;const{signal:e}=t;this._loading=!0,this._loadError=null;try{const[t,o]=await Promise.all([bt(this.hass),ft(this.hass)]);if(e.aborted)return;if(this._sensors=t,this._alarms=o,this.action&&this._selectedSensors.length>0){const e=new Set;for(const[o,i]of Object.entries(t))(i??[]).some(t=>this._selectedSensors.includes(t.entity_id))&&e.add(o);this._expandedCategories=e}}catch(t){if(e.aborted)return;this._loadError=t instanceof Error?t.message:"Failed to load sensors and alarms"}finally{e.aborted||(this._loading=!1)}}_populateForm(){this.action&&(this._name=this.action.name,this._modes=[...this.action.modes],this._delaySeconds=this.action.delay_seconds,this._selectedSensors=[...this.action.sensor_entity_ids],this._selectedAlarms=this.action.alarm_entity_ids.slice(0,1))}_toggleMode(t){this._modes=Ht(this._modes,t),this._clearError("modes")}_toggleSensor(t){this._selectedSensors=Ht(this._selectedSensors,t),this._clearError("sensors")}_openMoreInfo(t,e){e.stopPropagation(),this.dispatchEvent(new CustomEvent("hass-more-info",{detail:{entityId:t},bubbles:!0,composed:!0}))}_selectAlarm(t){this._selectedAlarms=[t],this._clearError("alarms")}_isCategorySelected(t,e){if(!this._sensors)return!1;const o=e??this._sensors[t]??[];return 0!==o.length&&o.every(t=>this._selectedSensors.includes(t.entity_id))}_isCategoryPartial(t,e){if(!this._sensors)return!1;const o=e??this._sensors[t]??[];if(0===o.length)return!1;const i=o.filter(t=>this._selectedSensors.includes(t.entity_id));return i.length>0&&i.length<o.length}_toggleCategory(t,e){if(!this._sensors)return;const o=e??this._sensors[t]??[],i=o.map(t=>t.entity_id);if(this._isCategorySelected(t,o))this._selectedSensors=this._selectedSensors.filter(t=>!i.includes(t));else{const t=i.filter(t=>!this._selectedSensors.includes(t));this._selectedSensors=[...this._selectedSensors,...t]}this._clearError("sensors")}_toggleCategoryExpanded(t){const e=new Set(this._expandedCategories);e.has(t)?e.delete(t):e.add(t),this._expandedCategories=e}_clearError(t){if(this._errors[t]){const{[t]:e,...o}=this._errors;this._errors=o}}_validate(){return this._errors={},this._name.trim()||(this._errors={...this._errors,name:"Name is required"}),0===this._modes.length&&(this._errors={...this._errors,modes:"Select at least one mode"}),0===this._selectedSensors.length&&(this._errors={...this._errors,sensors:"Select at least one sensor"}),0===this._selectedAlarms.length&&(this._errors={...this._errors,alarms:"Select an alarm"}),0===Object.keys(this._errors).length}async _handleSave(){if(!this._saving&&this._validate()){this._saving=!0;try{const t={name:this._name.trim(),modes:this._modes,delay_seconds:this._delaySeconds,sensor_entity_ids:this._selectedSensors,alarm_entity_ids:this._selectedAlarms};this.action?await _t(this.hass,this.action.id,t):await async function(t,e){return t.callWS({type:"abode_security/actions/create",...e})}(this.hass,t),this.dispatchEvent(new CustomEvent("save"))}catch(t){console.error("Failed to save action:",t),this._errors={...this._errors,form:t instanceof Error?t.message:"Failed to save"}}finally{this._saving=!1}}}_handleCancel(){this.dispatchEvent(new CustomEvent("cancel"))}render(){return B`
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
          @input=${t=>{this._name=t.target.value,this._clearError("name")}}
          class=${this._errors.name?"error":""}
          placeholder="Enter action name"
        />
        ${this._errors.name?B`<span class="error-text">${this._errors.name}</span>`:""}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${Nt.map(t=>B`
              <label>
                <input
                  type="checkbox"
                  .checked=${this._modes.includes(t)}
                  @change=${()=>this._toggleMode(t)}
                />
                ${t.charAt(0).toUpperCase()+t.slice(1)}
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
            @input=${t=>{this._delaySeconds=Number(t.target.value)}}
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
        <label>Alarm to trigger (required)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms?B`<span class="error-text">${this._errors.alarms}</span>`:""}
      </div>

      ${this._errors.form?B`<div class="error-text" style="margin-bottom: 16px;">${this._errors.form}</div>`:""}
    `}_renderFooter(){return B`
      <button slot="footer" class="cancel" @click=${this._handleCancel}>Cancel</button>
      <button slot="footer" class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
        ${this._saving?"Saving...":"Save"}
      </button>
    `}_renderSensorSelection(){const t=this._sensors;if(!t)return B`<div class="loading">Loading sensors...</div>`;const e=Object.keys(t).filter(e=>(t[e]??[]).length>0).sort(jt);if(0===e.length)return B`<div class="loading">No sensors available</div>`;const o=this._sensorSearch.trim().toLowerCase(),i=o.length>0,r=t=>Ft(Rt(this.hass,t.entity_id,t.state)),s=e.map(e=>{const s=t[e]??[],n=i?s.filter(t=>t.name.toLowerCase().includes(o)):s,a=n.filter(t=>!r(t)),l=n.filter(t=>r(t)),c=[...a,...l],d=s.filter(r).length;return{category:e,sensors:s,filtered:n,ordered:c,unavailableTotal:d}}).filter(({filtered:t})=>!i||t.length>0),n=B`
      <input
        type="search"
        class="sensor-search"
        aria-label="Search sensors"
        placeholder="Search sensors…"
        autocomplete="off"
        spellcheck="false"
        .value=${this._sensorSearch}
        @input=${t=>{this._sensorSearch=t.target.value}}
      />
    `;return 0===s.length?B`
        ${n}
        <div class="loading">No sensors match “${this._sensorSearch}”</div>
      `:B`
      ${n}
      <div class="sensor-categories">
        ${s.map(({category:t,sensors:e,filtered:o,ordered:r,unavailableTotal:s},n)=>{const a=`sensor-cat-${n}-${t.replace(/[^A-Za-z0-9_-]/g,"-")}`,l=t.replace(/_/g," "),c=i||this._expandedCategories.has(t),d=o.length===e.length?`(${e.length})`:`(${o.length}/${e.length})`,h=s>0?B` <span class="unavailable-count">${s} unavailable</span>`:W;return B`
              <div class="category">
                <div
                  class="category-header"
                  @click=${()=>this._toggleCategory(t,o)}
                >
                  <input
                    type="checkbox"
                    .checked=${this._isCategorySelected(t,o)}
                    .indeterminate=${this._isCategoryPartial(t,o)}
                    @click=${t=>t.stopPropagation()}
                    @change=${()=>this._toggleCategory(t,o)}
                  />
                  <span>${l} ${d}${h}</span>
                  ${i?null:B`
                        <button
                          type="button"
                          class="disclosure"
                          aria-expanded=${c?"true":"false"}
                          aria-controls=${c?a:W}
                          aria-label=${c?`Collapse ${l}`:`Expand ${l}`}
                          @click=${e=>{e.stopPropagation(),this._toggleCategoryExpanded(t)}}
                        >
                          <span aria-hidden="true">▸</span>
                        </button>
                      `}
                </div>
                ${c?B`
                      <div id=${a} class="category-items">
                        ${r.map(e=>this._renderSensorRow(e,t))}
                      </div>
                    `:null}
              </div>
            `})}
      </div>
    `}_renderSensorRow(t,e){const o=Rt(this.hass,t.entity_id,t.state),i=Ft(o),r=i?"unavailable":"on"===o?"on":"off",s=function(t,e){if(Ft(t))return"unavailable";const o=Lt[e];return o?"on"===t?o.on:"off"===t?o.off:t:t}(o,e);return B`
      <div class="sensor-row ${i?"unavailable":""}">
        <label>
          <input
            type="checkbox"
            .checked=${this._selectedSensors.includes(t.entity_id)}
            @change=${()=>this._toggleSensor(t.entity_id)}
          />
          <span class="entity-name">${t.name}</span>
          <!-- Area column always rendered (even when empty) so the
               state-pill column lines up across rows that do and don't
               have an area assigned. Empty cells get aria-hidden="true"
               so screen readers skip them — the cell exists only for
               layout, not for semantics. ARIA attributes are enumerated
               (string "true"/"false"), not HTML boolean attributes, so
               we set the value explicitly when needed and omit the
               attribute entirely via Lit's nothing sentinel otherwise. -->
          <span class="entity-area" aria-hidden=${t.area?W:"true"}>
            ${t.area??W}
          </span>
          <span class="state-pill ${r}" aria-label="${t.name} state: ${s}">
            ${i?B`<ha-icon icon="mdi:alert-circle-outline" aria-hidden="true"></ha-icon>`:W}
            ${s}
          </span>
        </label>
        <button
          type="button"
          class="info-button"
          aria-label="More info for ${t.name}"
          title="More info"
          @click=${e=>this._openMoreInfo(t.entity_id,e)}
        >
          <ha-icon icon="mdi:information-outline"></ha-icon>
        </button>
      </div>
    `}_renderAlarmSelection(){if(0===this._alarms.length)return B`<div class="loading">No alarms available</div>`;const t=this._alarms.map(t=>({entity_id:t.entity_id,label:t.name.replace(/^Abode Alarm\s+/i,"")})).sort((t,e)=>t.label.localeCompare(e.label));return B`
      <div class="alarm-list" role="radiogroup" aria-label="Alarm to trigger">
        ${t.map(t=>B`
            <label>
              <input
                type="radio"
                name="abode-action-alarm"
                value=${t.entity_id}
                .checked=${this._selectedAlarms.includes(t.entity_id)}
                @change=${()=>this._selectAlarm(t.entity_id)}
              />
              ${t.label}
            </label>
          `)}
      </div>
    `}};Bt.styles=n`
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
  `,t([pt({attribute:!1})],Bt.prototype,"hass",void 0),t([pt({attribute:!1})],Bt.prototype,"action",void 0),t([ut()],Bt.prototype,"_name",void 0),t([ut()],Bt.prototype,"_modes",void 0),t([ut()],Bt.prototype,"_delaySeconds",void 0),t([ut()],Bt.prototype,"_selectedSensors",void 0),t([ut()],Bt.prototype,"_selectedAlarms",void 0),t([ut()],Bt.prototype,"_sensors",void 0),t([ut()],Bt.prototype,"_alarms",void 0),t([ut()],Bt.prototype,"_errors",void 0),t([ut()],Bt.prototype,"_saving",void 0),t([ut()],Bt.prototype,"_loading",void 0),t([ut()],Bt.prototype,"_loadError",void 0),t([ut()],Bt.prototype,"_expandedCategories",void 0),t([ut()],Bt.prototype,"_sensorSearch",void 0),Bt=t([ct("abode-action-editor")],Bt);let qt=class extends at{constructor(){super(...arguments),this._actions=[],this._loading=!0,this._error=null,this._editingAction=null,this._showEditor=!1,this._confirm=null,this._togglingIds=new Set,this._operationError=null,this._abort=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}disconnectedCallback(){this._abort?.abort(),this._abort=null,super.disconnectedCallback()}async _loadData(){this._abort?.abort();const t=new AbortController;this._abort=t;const{signal:e}=t;this._loading=!0,this._error=null;try{const t=await gt(this.hass);if(e.aborted)return;this._actions=t}catch(t){if(e.aborted)return;this._error=t instanceof Error?t.message:"Failed to load actions"}finally{e.aborted||(this._loading=!1)}}_getRecentTriggers(){return this._actions.filter(t=>t.last_triggered).sort((t,e)=>new Date(e.last_triggered).getTime()-new Date(t.last_triggered).getTime()).slice(0,5)}_formatTime(t){if(!t)return"";const e=new Date(t),o=(new Date).getTime()-e.getTime(),i=Math.floor(o/6e4),r=Math.floor(o/36e5),s=Math.floor(o/864e5);return i<1?"Just now":i<60?`${i}m ago`:r<24?`${r}h ago`:s<7?`${s}d ago`:e.toLocaleDateString()}_addAction(){this._editingAction=null,this._showEditor=!0}_editAction(t){this._editingAction=t,this._showEditor=!0}async _toggleAction(t){const e=t.id;this._togglingIds=new Set([...this._togglingIds,e]),this._operationError=null;try{const o=await _t(this.hass,e,{enabled:!t.enabled});this._actions=this._actions.map(t=>t.id===e?o:t)}catch(e){console.error("Failed to toggle action:",e),this._operationError=`Failed to ${t.enabled?"disable":"enable"} action`}finally{this._togglingIds=new Set([...this._togglingIds].filter(t=>t!==e))}}_requestDelete(t){this._confirm={kind:"delete",action:t}}async _confirmDelete(){if("delete"!==this._confirm?.kind)return;const{action:t}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/delete",action_id:e})}(this.hass,t.id),this._actions=this._actions.filter(e=>e.id!==t.id)}catch(t){console.error("Failed to delete action:",t),this._operationError="Failed to delete action"}}_requestTest(t){this._confirm={kind:"test",action:t}}async _confirmTest(){if("test"!==this._confirm?.kind)return;const{action:t}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/test",action_id:e})}(this.hass,t.id)}catch(t){console.error("Failed to test action:",t),this._operationError="Failed to test action"}}_closeEditor(){this._showEditor=!1,this._editingAction=null}async _handleSave(){this._closeEditor(),await this._loadData()}render(){if(this._loading)return B`<div class="loading">Loading actions...</div>`;if(this._error)return B`<div class="error" role="alert">${this._error}</div>`;const t=this._getRecentTriggers();return B`
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
              ${Ut(this._actions,t=>t.id,t=>this._renderActionRow(t))}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${0===t.length?B`<div class="empty-state" style="padding: 24px;">No recent triggers</div>`:B`
              <div class="trigger-list">
                ${t.map(t=>B`
                    <div class="trigger-item">
                      <span class="trigger-name">${t.name}</span>
                      <span class="trigger-time">${this._formatTime(t.last_triggered)}</span>
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
    `}_renderActionRow(t){const e=this._togglingIds.has(t.id),o=t.sensor_entity_ids.filter(t=>Ft(Rt(this.hass,t))).length,i=t.sensor_entity_ids.length;return B`
      <div class="action-row ${t.enabled?"":"disabled"}" role="listitem">
        <div class="action-info">
          <div class="action-name">${t.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${t.modes.map(t=>B`<span class="mode-chip">${t}</span>`)}
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
          </div>
        </div>
        <div class="action-controls">
          <label class="toggle-switch">
            <input
              type="checkbox"
              .checked=${t.enabled}
              .disabled=${e}
              @change=${()=>this._toggleAction(t)}
              aria-label="${t.enabled?"Disable":"Enable"} action"
            />
            <span class="toggle-slider"></span>
          </label>
          <button
            class="icon-button"
            @click=${()=>this._requestTest(t)}
            title="Test"
            aria-label="Test action"
          >
            <ha-icon icon="mdi:play"></ha-icon>
          </button>
          <button
            class="icon-button"
            @click=${()=>this._editAction(t)}
            title="Edit"
            aria-label="Edit action"
          >
            <ha-icon icon="mdi:pencil"></ha-icon>
          </button>
          <button
            class="icon-button delete"
            @click=${()=>this._requestDelete(t)}
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
    `}};qt.styles=n`
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
  `,t([pt({attribute:!1})],qt.prototype,"hass",void 0),t([ut()],qt.prototype,"_actions",void 0),t([ut()],qt.prototype,"_loading",void 0),t([ut()],qt.prototype,"_error",void 0),t([ut()],qt.prototype,"_editingAction",void 0),t([ut()],qt.prototype,"_showEditor",void 0),t([ut()],qt.prototype,"_confirm",void 0),t([ut()],qt.prototype,"_togglingIds",void 0),t([ut()],qt.prototype,"_operationError",void 0),qt=t([ct("abode-actions-tab")],qt);let Wt=class extends at{constructor(){super(...arguments),this._activeTab="modes"}render(){const t="modes"===this._activeTab?"modes-panel":"actions-panel";return B`
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
            @click=${()=>this._activeTab="modes"}
          >
            Modes
          </button>
          <button
            role="tab"
            id="actions-tab"
            aria-selected=${"actions"===this._activeTab}
            aria-controls="actions-panel"
            class=${"actions"===this._activeTab?"active":""}
            @click=${()=>this._activeTab="actions"}
          >
            Actions
          </button>
        </div>

        <div
          class="tab-content"
          role="tabpanel"
          id=${t}
          aria-labelledby=${"modes"===this._activeTab?"modes-tab":"actions-tab"}
        >
          ${"modes"===this._activeTab?B`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`:B`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`}
        </div>
      </div>
    `}};Wt.styles=n`
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
  `,t([pt({attribute:!1})],Wt.prototype,"hass",void 0),t([ut()],Wt.prototype,"_activeTab",void 0),Wt=t([ct("abode-configuration-panel")],Wt);export{Wt as AbodeConfigurationPanel};
