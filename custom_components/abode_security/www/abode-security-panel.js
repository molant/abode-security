function t(t,e,i,o){var s,r=arguments.length,a=r<3?e:null===o?o=Object.getOwnPropertyDescriptor(e,i):o;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(t,e,i,o);else for(var n=t.length-1;n>=0;n--)(s=t[n])&&(a=(r<3?s(a):r>3?s(e,i,a):s(e,i))||a);return r>3&&a&&Object.defineProperty(e,i,a),a}"function"==typeof SuppressedError&&SuppressedError;const e=globalThis,i=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,o=Symbol(),s=new WeakMap;let r=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==o)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(i&&void 0===t){const i=void 0!==e&&1===e.length;i&&(t=s.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&s.set(e,t))}return t}toString(){return this.cssText}};const a=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,i,o)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+t[o+1],t[0]);return new r(i,t,o)},n=i?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const i of t.cssRules)e+=i.cssText;return(t=>new r("string"==typeof t?t:t+"",void 0,o))(e)})(t):t,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:g}=Object,u=globalThis,_=u.trustedTypes,m=_?_.emptyScript:"",b=u.reactiveElementPolyfillSupport,f=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?m:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let i=t;switch(e){case Boolean:i=null!==t;break;case Number:i=null===t?null:Number(t);break;case Object:case Array:try{i=JSON.parse(t)}catch(t){i=null}}return i}},v=(t,e)=>!l(t,e),x={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=x){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const i=Symbol(),o=this.getPropertyDescriptor(t,i,e);void 0!==o&&c(this.prototype,t,o)}}static getPropertyDescriptor(t,e,i){const{get:o,set:s}=d(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:o,set(e){const r=o?.call(this);s?.call(this,e),this.requestUpdate(t,r,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??x}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const t=g(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const i of e)this.createProperty(i,t[i])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,i]of e)this.elementProperties.set(t,i)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const i=this._$Eu(t,e);void 0!==i&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const i=new Set(t.flat(1/0).reverse());for(const t of i)e.unshift(n(t))}else void 0!==t&&e.push(n(t));return e}static _$Eu(t,e){const i=e.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,o)=>{if(i)t.adoptedStyleSheets=o.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const i of o){const o=document.createElement("style"),s=e.litNonce;void 0!==s&&o.setAttribute("nonce",s),o.textContent=i.cssText,t.appendChild(o)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){const i=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,i);if(void 0!==o&&!0===i.reflect){const s=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(e,i.type);this._$Em=t,null==s?this.removeAttribute(o):this.setAttribute(o,s),this._$Em=null}}_$AK(t,e){const i=this.constructor,o=i._$Eh.get(t);if(void 0!==o&&this._$Em!==o){const t=i.getPropertyOptions(o),s="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=o;const r=s.fromAttribute(e,t.type);this[o]=r??this._$Ej?.get(o)??r,this._$Em=null}}requestUpdate(t,e,i,o=!1,s){if(void 0!==t){const r=this.constructor;if(!1===o&&(s=this[t]),i??=r.getPropertyOptions(t),!((i.hasChanged??v)(s,e)||i.useDefault&&i.reflect&&s===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,i))))return;this.C(t,e,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:o,wrapped:s},r){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==s||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),!0===o&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,i]of t){const{wrapped:t}=i,o=this[e];!0!==t||this._$AL.has(e)||void 0===o||this.C(e,void 0,i,o)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[f("elementProperties")]=new Map,$[f("finalized")]=new Map,b?.({ReactiveElement:$}),(u.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,A=t=>t,S=w.trustedTypes,k=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,E="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,P=`<${T}>`,D=document,z=()=>D.createComment(""),M=t=>null===t||"object"!=typeof t&&"function"!=typeof t,O=Array.isArray,U="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,H=/>/g,j=RegExp(`>|${U}(?:([^\\s"'>=/]+)(${U}*=${U}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),I=/'/g,L=/"/g,F=/^(?:script|style|textarea|title)$/i,q=(t=>(e,...i)=>({_$litType$:t,strings:e,values:i}))(1),W=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),V=new WeakMap,K=D.createTreeWalker(D,129);function J(t,e){if(!O(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==k?k.createHTML(e):e}const Z=(t,e)=>{const i=t.length-1,o=[];let s,r=2===e?"<svg>":3===e?"<math>":"",a=N;for(let e=0;e<i;e++){const i=t[e];let n,l,c=-1,d=0;for(;d<i.length&&(a.lastIndex=d,l=a.exec(i),null!==l);)d=a.lastIndex,a===N?"!--"===l[1]?a=R:void 0!==l[1]?a=H:void 0!==l[2]?(F.test(l[2])&&(s=RegExp("</"+l[2],"g")),a=j):void 0!==l[3]&&(a=j):a===j?">"===l[0]?(a=s??N,c=-1):void 0===l[1]?c=-2:(c=a.lastIndex-l[2].length,n=l[1],a=void 0===l[3]?j:'"'===l[3]?L:I):a===L||a===I?a=j:a===R||a===H?a=N:(a=j,s=void 0);const h=a===j&&t[e+1].startsWith("/>")?" ":"";r+=a===N?i+P:c>=0?(o.push(n),i.slice(0,c)+E+i.slice(c)+C+h):i+C+(-2===c?e:h)}return[J(t,r+(t[i]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),o]};class X{constructor({strings:t,_$litType$:e},i){let o;this.parts=[];let s=0,r=0;const a=t.length-1,n=this.parts,[l,c]=Z(t,e);if(this.el=X.createElement(l,i),K.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(o=K.nextNode())&&n.length<a;){if(1===o.nodeType){if(o.hasAttributes())for(const t of o.getAttributeNames())if(t.endsWith(E)){const e=c[r++],i=o.getAttribute(t).split(C),a=/([.?@])?(.*)/.exec(e);n.push({type:1,index:s,name:a[2],strings:i,ctor:"."===a[1]?et:"?"===a[1]?it:"@"===a[1]?ot:tt}),o.removeAttribute(t)}else t.startsWith(C)&&(n.push({type:6,index:s}),o.removeAttribute(t));if(F.test(o.tagName)){const t=o.textContent.split(C),e=t.length-1;if(e>0){o.textContent=S?S.emptyScript:"";for(let i=0;i<e;i++)o.append(t[i],z()),K.nextNode(),n.push({type:2,index:++s});o.append(t[e],z())}}}else if(8===o.nodeType)if(o.data===T)n.push({type:2,index:s});else{let t=-1;for(;-1!==(t=o.data.indexOf(C,t+1));)n.push({type:7,index:s}),t+=C.length-1}s++}}static createElement(t,e){const i=D.createElement("template");return i.innerHTML=t,i}}function G(t,e,i=t,o){if(e===W)return e;let s=void 0!==o?i._$Co?.[o]:i._$Cl;const r=M(e)?void 0:e._$litDirective$;return s?.constructor!==r&&(s?._$AO?.(!1),void 0===r?s=void 0:(s=new r(t),s._$AT(t,i,o)),void 0!==o?(i._$Co??=[])[o]=s:i._$Cl=s),void 0!==s&&(e=G(t,s._$AS(t,e.values),s,o)),e}class Q{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:i}=this._$AD,o=(t?.creationScope??D).importNode(e,!0);K.currentNode=o;let s=K.nextNode(),r=0,a=0,n=i[0];for(;void 0!==n;){if(r===n.index){let e;2===n.type?e=new Y(s,s.nextSibling,this,t):1===n.type?e=new n.ctor(s,n.name,n.strings,this,t):6===n.type&&(e=new st(s,this,t)),this._$AV.push(e),n=i[++a]}r!==n?.index&&(s=K.nextNode(),r++)}return K.currentNode=D,o}p(t){let e=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,o){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=G(this,t,e),M(t)?t===B||null==t||""===t?(this._$AH!==B&&this._$AR(),this._$AH=B):t!==this._$AH&&t!==W&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>O(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==B&&M(this._$AH)?this._$AA.nextSibling.data=t:this.T(D.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:i}=t,o="number"==typeof i?this._$AC(t):(void 0===i.el&&(i.el=X.createElement(J(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===o)this._$AH.p(e);else{const t=new Q(o,this),i=t.u(this.options);t.p(e),this.T(i),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new X(t)),e}k(t){O(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let i,o=0;for(const s of t)o===e.length?e.push(i=new Y(this.O(z()),this.O(z()),this,this.options)):i=e[o],i._$AI(s),o++;o<e.length&&(this._$AR(i&&i._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=A(t).nextSibling;A(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class tt{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,o,s){this.type=1,this._$AH=B,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=s,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=B}_$AI(t,e=this,i,o){const s=this.strings;let r=!1;if(void 0===s)t=G(this,t,e,0),r=!M(t)||t!==this._$AH&&t!==W,r&&(this._$AH=t);else{const o=t;let a,n;for(t=s[0],a=0;a<s.length-1;a++)n=G(this,o[i+a],e,a),n===W&&(n=this._$AH[a]),r||=!M(n)||n!==this._$AH[a],n===B?t=B:t!==B&&(t+=(n??"")+s[a+1]),this._$AH[a]=n}r&&!o&&this.j(t)}j(t){t===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class et extends tt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===B?void 0:t}}class it extends tt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==B)}}class ot extends tt{constructor(t,e,i,o,s){super(t,e,i,o,s),this.type=5}_$AI(t,e=this){if((t=G(this,t,e,0)??B)===W)return;const i=this._$AH,o=t===B&&i!==B||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,s=t!==B&&(i===B||o);o&&this.element.removeEventListener(this.name,this,i),s&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class st{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){G(this,t)}}const rt=w.litHtmlPolyfillSupport;rt?.(X,Y),(w.litHtmlVersions??=[]).push("3.3.2");const at=globalThis;class nt extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,i)=>{const o=i?.renderBefore??e;let s=o._$litPart$;if(void 0===s){const t=i?.renderBefore??null;o._$litPart$=s=new Y(e.insertBefore(z(),t),t,void 0,i??{})}return s._$AI(t),s})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}}nt._$litElement$=!0,nt.finalized=!0,at.litElementHydrateSupport?.({LitElement:nt});const lt=at.litElementPolyfillSupport;lt?.({LitElement:nt}),(at.litElementVersions??=[]).push("4.2.2");const ct=t=>(e,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},dt={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},ht=(t=dt,e,i)=>{const{kind:o,metadata:s}=i;let r=globalThis.litPropertyMetadata.get(s);if(void 0===r&&globalThis.litPropertyMetadata.set(s,r=new Map),"setter"===o&&((t=Object.create(t)).wrapped=!0),r.set(i.name,t),"accessor"===o){const{name:o}=i;return{set(i){const s=e.get.call(this);e.set.call(this,i),this.requestUpdate(o,s,t,!0,i)},init(e){return void 0!==e&&this.C(o,void 0,t,e),e}}}if("setter"===o){const{name:o}=i;return function(i){const s=this[o];e.call(this,i),this.requestUpdate(o,s,t,!0,i)}}throw Error("Unsupported decorator location: "+o)};function pt(t){return(e,i)=>"object"==typeof i?ht(t,e,i):((t,e,i)=>{const o=e.hasOwnProperty(i);return e.constructor.createProperty(i,t),o?Object.getOwnPropertyDescriptor(e,i):void 0})(t,e,i)}function gt(t){return pt({...t,state:!0,attribute:!1})}async function ut(t){return(await t.callWS({type:"abode_security/actions/list"})).actions}async function _t(t){return(await t.callWS({type:"abode_security/modes/list"})).modes}async function mt(t){return(await t.callWS({type:"abode_security/entities/sensors"})).sensors}async function bt(t){return(await t.callWS({type:"abode_security/entities/alarms"})).alarms}async function ft(t,e,i){return(await t.callWS({type:"abode_security/actions/update",action_id:e,...i})).action}let yt=class extends nt{constructor(){super(...arguments),this._modes=[],this._actions=[],this._loading=!0,this._error=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}async _loadData(){this._loading=!0,this._error=null;try{const[t,e]=await Promise.all([_t(this.hass),ut(this.hass)]);this._modes=t??[],this._actions=e??[]}catch(t){this._error=t instanceof Error?t.message:"Failed to load data"}finally{this._loading=!1}}_getActionsForMode(t){return this._actions.filter(e=>e.enabled&&e.modes.includes(t))}render(){return this._loading?q`<div class="loading">Loading modes...</div>`:this._error?q`<div class="error" role="alert">${this._error}</div>`:q`
      <div class="modes-grid">
        ${this._modes.map(t=>this._renderModeCard(t))}
      </div>
    `}_renderModeCard(t){const e=this._getActionsForMode(t.id);return q`
      <div class="mode-card ${t.active?"active":""}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${t.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${t.name}</h3>
            <div class="badges">
              <span class="badge">${t.action_count} actions</span>
              ${t.active?q`<span class="badge active">Active</span>`:""}
            </div>
          </div>
        </div>

        ${e.length>0?q`
              <ul class="action-list" aria-label="Actions for ${t.name} mode">
                ${e.map(t=>q`
                    <li>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${t.name}
                    </li>
                  `)}
              </ul>
            `:q`<div class="empty-actions">No actions configured</div>`}
      </div>
    `}};yt.styles=a`
    :host {
      display: block;
    }

    .modes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }

    .mode-card {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      border: 2px solid transparent;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .mode-card.active {
      border-color: var(--primary-color, #03a9f4);
      box-shadow: 0 4px 12px rgba(3, 169, 244, 0.2);
    }

    .mode-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .mode-icon {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--primary-color, #03a9f4);
      color: white;
      border-radius: 50%;
    }

    .mode-icon ha-icon {
      --mdc-icon-size: 24px;
    }

    .mode-info h3 {
      margin: 0;
      font-size: 18px;
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
      margin: 16px 0 0 0;
      padding: 0;
      list-style: none;
    }

    .action-list li {
      padding: 8px 0;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
      font-size: 14px;
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
  `,t([pt({attribute:!1})],yt.prototype,"hass",void 0),t([gt()],yt.prototype,"_modes",void 0),t([gt()],yt.prototype,"_actions",void 0),t([gt()],yt.prototype,"_loading",void 0),t([gt()],yt.prototype,"_error",void 0),yt=t([ct("abode-modes-tab")],yt);let vt=class extends nt{constructor(){super(...arguments),this.action=null,this._name="",this._modes=[],this._delaySeconds=0,this._selectedSensors=[],this._selectedAlarms=[],this._sensors=null,this._alarms=[],this._errors={},this._saving=!1,this._loading=!0}async connectedCallback(){super.connectedCallback(),await this._loadEntities(),this.action&&this._populateForm()}async _loadEntities(){this._loading=!0;try{const[t,e]=await Promise.all([mt(this.hass),bt(this.hass)]);this._sensors=t??null,this._alarms=e??[]}catch(t){console.error("Failed to load entities:",t)}finally{this._loading=!1}}_populateForm(){this.action&&(this._name=this.action.name,this._modes=[...this.action.modes],this._delaySeconds=this.action.delay_seconds,this._selectedSensors=[...this.action.sensor_entity_ids],this._selectedAlarms=[...this.action.alarm_entity_ids])}_toggleMode(t){this._modes.includes(t)?this._modes=this._modes.filter(e=>e!==t):this._modes=[...this._modes,t],this._clearError("modes")}_toggleSensor(t){this._selectedSensors.includes(t)?this._selectedSensors=this._selectedSensors.filter(e=>e!==t):this._selectedSensors=[...this._selectedSensors,t],this._clearError("sensors")}_toggleAlarm(t){this._selectedAlarms.includes(t)?this._selectedAlarms=this._selectedAlarms.filter(e=>e!==t):this._selectedAlarms=[...this._selectedAlarms,t],this._clearError("alarms")}_isCategorySelected(t){if(!this._sensors)return!1;const e=this._sensors[t]||[];return 0!==e.length&&e.every(t=>this._selectedSensors.includes(t.entity_id))}_isCategoryPartial(t){if(!this._sensors)return!1;const e=this._sensors[t]||[];if(0===e.length)return!1;const i=e.filter(t=>this._selectedSensors.includes(t.entity_id));return i.length>0&&i.length<e.length}_toggleCategory(t){if(!this._sensors)return;const e=(this._sensors[t]||[]).map(t=>t.entity_id);if(this._isCategorySelected(t))this._selectedSensors=this._selectedSensors.filter(t=>!e.includes(t));else{const t=e.filter(t=>!this._selectedSensors.includes(t));this._selectedSensors=[...this._selectedSensors,...t]}this._clearError("sensors")}_clearError(t){if(this._errors[t]){const{[t]:e,...i}=this._errors;this._errors=i}}_validate(){return this._errors={},this._name.trim()||(this._errors={...this._errors,name:"Name is required"}),0===this._modes.length&&(this._errors={...this._errors,modes:"Select at least one mode"}),0===this._selectedSensors.length&&(this._errors={...this._errors,sensors:"Select at least one sensor"}),0===this._selectedAlarms.length&&(this._errors={...this._errors,alarms:"Select at least one alarm"}),0===Object.keys(this._errors).length}async _handleSave(){if(this._validate()){this._saving=!0;try{const t={name:this._name.trim(),modes:this._modes,delay_seconds:this._delaySeconds,sensor_entity_ids:this._selectedSensors,alarm_entity_ids:this._selectedAlarms};this.action?await ft(this.hass,this.action.id,t):await async function(t,e){return(await t.callWS({type:"abode_security/actions/create",...e})).action}(this.hass,t),this.dispatchEvent(new CustomEvent("save"))}catch(t){console.error("Failed to save action:",t),this._errors={...this._errors,form:t instanceof Error?t.message:"Failed to save"}}finally{this._saving=!1}}}_handleCancel(){this.dispatchEvent(new CustomEvent("cancel"))}_handleOverlayClick(t){t.target===t.currentTarget&&this._handleCancel()}_handleKeydown(t){"Escape"===t.key&&this._handleCancel()}render(){return q`
      <div
        class="editor-overlay"
        @click=${this._handleOverlayClick}
        @keydown=${this._handleKeydown}
      >
        <div class="editor-dialog" role="dialog" aria-modal="true" aria-labelledby="editor-title">
          <h2 id="editor-title">${this.action?"Edit Action":"New Action"}</h2>

          ${this._loading?q`<div class="loading">Loading...</div>`:this._renderForm()}
        </div>
      </div>
    `}_renderForm(){return q`
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
        ${this._errors.name?q`<span class="error-text">${this._errors.name}</span>`:""}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${["standby","home","away"].map(t=>q`
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
        ${this._errors.modes?q`<span class="error-text">${this._errors.modes}</span>`:""}
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
        ${this._errors.sensors?q`<span class="error-text">${this._errors.sensors}</span>`:""}
      </div>

      <div class="form-group">
        <label>Alarms to trigger (at least one required)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms?q`<span class="error-text">${this._errors.alarms}</span>`:""}
      </div>

      ${this._errors.form?q`<div class="error-text" style="margin-bottom: 16px;">
            ${this._errors.form}
          </div>`:""}

      <div class="button-row">
        <button class="cancel" @click=${this._handleCancel}>Cancel</button>
        <button class="primary" @click=${this._handleSave} ?disabled=${this._saving}>
          ${this._saving?"Saving...":"Save"}
        </button>
      </div>
    `}_renderSensorSelection(){if(!this._sensors)return q`<div class="loading">Loading sensors...</div>`;const t=["door","window","motion","moisture","smoke","connectivity","other"].filter(t=>(this._sensors[t]||[]).length>0);return 0===t.length?q`<div class="loading">No sensors available</div>`:q`
      <div class="sensor-categories">
        ${t.map(t=>{const e=this._sensors[t]||[];return q`
            <div class="category">
              <div class="category-header" @click=${()=>this._toggleCategory(t)}>
                <input
                  type="checkbox"
                  .checked=${this._isCategorySelected(t)}
                  .indeterminate=${this._isCategoryPartial(t)}
                  @click=${t=>t.stopPropagation()}
                  @change=${()=>this._toggleCategory(t)}
                />
                <span>${t} (${e.length})</span>
              </div>
              <div class="category-items">
                ${e.map(t=>q`
                    <label>
                      <input
                        type="checkbox"
                        .checked=${this._selectedSensors.includes(t.entity_id)}
                        @change=${()=>this._toggleSensor(t.entity_id)}
                      />
                      ${t.name}
                    </label>
                  `)}
              </div>
            </div>
          `})}
      </div>
    `}_renderAlarmSelection(){return 0===this._alarms.length?q`<div class="loading">No alarms available</div>`:q`
      <div class="alarm-list">
        ${this._alarms.map(t=>q`
            <label>
              <input
                type="checkbox"
                .checked=${this._selectedAlarms.includes(t.entity_id)}
                @change=${()=>this._toggleAlarm(t.entity_id)}
              />
              ${t.name}
            </label>
          `)}
      </div>
    `}};vt.styles=a`
    :host {
      display: block;
    }

    .editor-overlay {
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

    .editor-dialog {
      background: var(--card-background-color, #fff);
      border-radius: 12px;
      padding: 24px;
      max-width: 600px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    h2 {
      margin: 0 0 24px 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
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

    .category-header input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
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

    .alarm-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
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

    .alarm-list input[type='checkbox'] {
      width: 16px;
      height: 16px;
      accent-color: var(--primary-color, #03a9f4);
    }

    .button-row {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .button-row button {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .button-row button.cancel {
      background: transparent;
      color: var(--secondary-text-color);
    }

    .button-row button.cancel:hover {
      background: var(--secondary-background-color);
    }

    .button-row button.primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    .button-row button.primary:hover:not(:disabled) {
      background: var(--primary-color-dark, #0288d1);
    }

    .button-row button.primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .button-row button:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }

    .loading {
      text-align: center;
      padding: 24px;
      color: var(--secondary-text-color);
    }
  `,t([pt({attribute:!1})],vt.prototype,"hass",void 0),t([pt({attribute:!1})],vt.prototype,"action",void 0),t([gt()],vt.prototype,"_name",void 0),t([gt()],vt.prototype,"_modes",void 0),t([gt()],vt.prototype,"_delaySeconds",void 0),t([gt()],vt.prototype,"_selectedSensors",void 0),t([gt()],vt.prototype,"_selectedAlarms",void 0),t([gt()],vt.prototype,"_sensors",void 0),t([gt()],vt.prototype,"_alarms",void 0),t([gt()],vt.prototype,"_errors",void 0),t([gt()],vt.prototype,"_saving",void 0),t([gt()],vt.prototype,"_loading",void 0),vt=t([ct("abode-action-editor")],vt);let xt=class extends nt{constructor(){super(...arguments),this._actions=[],this._loading=!0,this._error=null,this._editingAction=null,this._showEditor=!1,this._showDeleteConfirm=!1,this._showTestConfirm=!1,this._pendingAction=null,this._togglingIds=new Set,this._operationError=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}async _loadData(){this._loading=!0,this._error=null;try{this._actions=await ut(this.hass)??[]}catch(t){this._error=t instanceof Error?t.message:"Failed to load actions"}finally{this._loading=!1}}_getRecentTriggers(){return(this._actions??[]).filter(t=>t.last_triggered).sort((t,e)=>new Date(e.last_triggered).getTime()-new Date(t.last_triggered).getTime()).slice(0,5)}_formatTime(t){if(!t)return"";const e=new Date(t),i=(new Date).getTime()-e.getTime(),o=Math.floor(i/6e4),s=Math.floor(i/36e5),r=Math.floor(i/864e5);return o<1?"Just now":o<60?`${o}m ago`:s<24?`${s}h ago`:r<7?`${r}d ago`:e.toLocaleDateString()}_addAction(){this._editingAction=null,this._showEditor=!0}_editAction(t){this._editingAction=t,this._showEditor=!0}async _toggleAction(t){const e=t.id;this._togglingIds=new Set([...this._togglingIds,e]),this._operationError=null;try{const i=await ft(this.hass,e,{enabled:!t.enabled});this._actions=this._actions.map(t=>t.id===e?i:t)}catch(e){console.error("Failed to toggle action:",e),this._operationError=`Failed to ${t.enabled?"disable":"enable"} action`}finally{this._togglingIds=new Set([...this._togglingIds].filter(t=>t!==e))}}_requestDelete(t){this._pendingAction=t,this._showDeleteConfirm=!0}async _confirmDelete(){if(this._pendingAction){this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/delete",action_id:e})}(this.hass,this._pendingAction.id),this._actions=this._actions.filter(t=>t.id!==this._pendingAction.id)}catch(t){console.error("Failed to delete action:",t),this._operationError="Failed to delete action"}finally{this._showDeleteConfirm=!1,this._pendingAction=null}}}_requestTest(t){this._pendingAction=t,this._showTestConfirm=!0}async _confirmTest(){if(this._pendingAction){this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/test",action_id:e})}(this.hass,this._pendingAction.id)}catch(t){console.error("Failed to test action:",t),this._operationError="Failed to test action"}finally{this._showTestConfirm=!1,this._pendingAction=null}}}_closeEditor(){this._showEditor=!1,this._editingAction=null}async _handleSave(){this._closeEditor(),await this._loadData()}render(){if(this._loading)return q`<div class="loading">Loading actions...</div>`;if(this._error)return q`<div class="error" role="alert">${this._error}</div>`;const t=this._getRecentTriggers();return q`
      ${this._operationError?q`
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
        <button
          class="add-button"
          @click=${this._addAction}
          aria-label="Add new action"
        >
          <ha-icon icon="mdi:plus"></ha-icon>
          Add Action
        </button>
      </div>

      ${0===this._actions.length?q`
            <div class="empty-state">
              <ha-icon icon="mdi:bell-off-outline"></ha-icon>
              <p>No actions configured</p>
              <button class="add-button" @click=${this._addAction}>
                <ha-icon icon="mdi:plus"></ha-icon>
                Create your first action
              </button>
            </div>
          `:q`
            <div class="actions-list" role="list">
              ${this._actions.map(t=>this._renderActionRow(t))}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${0===t.length?q`<div class="empty-state" style="padding: 24px;">
              No recent triggers
            </div>`:q`
              <div class="trigger-list">
                ${t.map(t=>q`
                    <div class="trigger-item">
                      <span class="trigger-name">${t.name}</span>
                      <span class="trigger-time"
                        >${this._formatTime(t.last_triggered)}</span
                      >
                    </div>
                  `)}
              </div>
            `}
      </div>

      ${this._showEditor?q`
            <abode-action-editor
              .hass=${this.hass}
              .action=${this._editingAction}
              @save=${this._handleSave}
              @cancel=${this._closeEditor}
            ></abode-action-editor>
          `:""}
      ${this._showDeleteConfirm?this._renderDeleteDialog():""}
      ${this._showTestConfirm?this._renderTestDialog():""}
    `}_renderActionRow(t){const e=this._togglingIds.has(t.id);return q`
      <div class="action-row ${t.enabled?"":"disabled"}" role="listitem">
        <div class="action-info">
          <div class="action-name">${t.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${t.modes.map(t=>q`<span class="mode-chip">${t}</span>`)}
            </div>
            ${t.trigger_count>0?q`<span class="trigger-info"
                  >${t.trigger_count} triggers</span
                >`:""}
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
    `}_renderDeleteDialog(){return q`
      <div
        class="dialog-overlay"
        @click=${t=>{t.target===t.currentTarget&&(this._showDeleteConfirm=!1)}}
        @keydown=${t=>{"Escape"===t.key&&(this._showDeleteConfirm=!1)}}
      >
        <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
          <h3 id="delete-title">Delete Action</h3>
          <p>
            Delete action "${this._pendingAction?.name}"? This cannot be undone.
          </p>
          <div class="dialog-actions">
            <button
              class="dialog-button cancel"
              @click=${()=>this._showDeleteConfirm=!1}
            >
              Cancel
            </button>
            <button class="dialog-button danger" @click=${this._confirmDelete}>
              Delete
            </button>
          </div>
        </div>
      </div>
    `}_renderTestDialog(){return q`
      <div
        class="dialog-overlay"
        @click=${t=>{t.target===t.currentTarget&&(this._showTestConfirm=!1)}}
        @keydown=${t=>{"Escape"===t.key&&(this._showTestConfirm=!1)}}
      >
        <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="test-title">
          <h3 id="test-title">Test Action</h3>
          <p>
            This will trigger real alarms. Are you sure you want to test
            "${this._pendingAction?.name}"?
          </p>
          <div class="dialog-actions">
            <button
              class="dialog-button cancel"
              @click=${()=>this._showTestConfirm=!1}
            >
              Cancel
            </button>
            <button class="dialog-button primary" @click=${this._confirmTest}>
              Test
            </button>
          </div>
        </div>
      </div>
    `}};xt.styles=a`
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

    .trigger-info {
      font-size: 12px;
      color: var(--secondary-text-color);
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
      transition: background 0.2s, color 0.2s;
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

    /* Dialog styles */
    .dialog-overlay {
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
    }

    .dialog {
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 24px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .dialog h3 {
      margin: 0 0 16px 0;
      font-size: 18px;
      font-weight: 500;
      color: var(--primary-text-color);
    }

    .dialog p {
      margin: 0 0 24px 0;
      color: var(--secondary-text-color);
      line-height: 1.5;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

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
  `,t([pt({attribute:!1})],xt.prototype,"hass",void 0),t([gt()],xt.prototype,"_actions",void 0),t([gt()],xt.prototype,"_loading",void 0),t([gt()],xt.prototype,"_error",void 0),t([gt()],xt.prototype,"_editingAction",void 0),t([gt()],xt.prototype,"_showEditor",void 0),t([gt()],xt.prototype,"_showDeleteConfirm",void 0),t([gt()],xt.prototype,"_showTestConfirm",void 0),t([gt()],xt.prototype,"_pendingAction",void 0),t([gt()],xt.prototype,"_togglingIds",void 0),t([gt()],xt.prototype,"_operationError",void 0),xt=t([ct("abode-actions-tab")],xt);let $t=class extends nt{constructor(){super(...arguments),this._activeTab="actions",this._activeTabId="actions-panel"}updated(t){super.updated(t),t.has("_activeTab")&&(this._activeTabId="modes"===this._activeTab?"modes-panel":"actions-panel")}render(){return q`
      <div class="panel-content">
        <div class="header">
          <h1>Abode Configuration</h1>
        </div>

        <div class="tab-bar" role="tablist">
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
        </div>

        <div
          class="tab-content"
          role="tabpanel"
          id=${this._activeTabId}
          aria-labelledby=${"modes"===this._activeTab?"modes-tab":"actions-tab"}
        >
          ${"modes"===this._activeTab?q`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`:q`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`}
        </div>
      </div>
    `}};$t.styles=a`
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
      transition: color 0.2s, border-color 0.2s;
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
  `,t([pt({attribute:!1})],$t.prototype,"hass",void 0),t([gt()],$t.prototype,"_activeTab",void 0),t([gt()],$t.prototype,"_activeTabId",void 0),$t=t([ct("abode-configuration-panel")],$t);export{$t as AbodeConfigurationPanel};
