function t(t,e,o,i){var s,r=arguments.length,a=r<3?e:null===i?i=Object.getOwnPropertyDescriptor(e,o):i;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(t,e,o,i);else for(var n=t.length-1;n>=0;n--)(s=t[n])&&(a=(r<3?s(a):r>3?s(e,o,a):s(e,o))||a);return r>3&&a&&Object.defineProperty(e,o,a),a}"function"==typeof SuppressedError&&SuppressedError;const e=globalThis,o=e.ShadowRoot&&(void 0===e.ShadyCSS||e.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,i=Symbol(),s=new WeakMap;let r=class{constructor(t,e,o){if(this._$cssResult$=!0,o!==i)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const e=this.t;if(o&&void 0===t){const o=void 0!==e&&1===e.length;o&&(t=s.get(e)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),o&&s.set(e,t))}return t}toString(){return this.cssText}};const a=(t,...e)=>{const o=1===t.length?t[0]:e.reduce((e,o,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+t[i+1],t[0]);return new r(o,t,i)},n=o?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const o of t.cssRules)e+=o.cssText;return(t=>new r("string"==typeof t?t:t+"",void 0,i))(e)})(t):t,{is:l,defineProperty:c,getOwnPropertyDescriptor:d,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,g=globalThis,m=g.trustedTypes,_=m?m.emptyScript:"",b=g.reactiveElementPolyfillSupport,f=(t,e)=>t,y={toAttribute(t,e){switch(e){case Boolean:t=t?_:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let o=t;switch(e){case Boolean:o=null!==t;break;case Number:o=null===t?null:Number(t);break;case Object:case Array:try{o=JSON.parse(t)}catch(t){o=null}}return o}},v=(t,e)=>!l(t,e),x={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:v};Symbol.metadata??=Symbol("metadata"),g.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=x){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const o=Symbol(),i=this.getPropertyDescriptor(t,o,e);void 0!==i&&c(this.prototype,t,i)}}static getPropertyDescriptor(t,e,o){const{get:i,set:s}=d(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const r=i?.call(this);s?.call(this,e),this.requestUpdate(t,r,o)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??x}static _$Ei(){if(this.hasOwnProperty(f("elementProperties")))return;const t=u(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(f("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(f("properties"))){const t=this.properties,e=[...h(t),...p(t)];for(const o of e)this.createProperty(o,t[o])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,o]of e)this.elementProperties.set(t,o)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const o=this._$Eu(t,e);void 0!==o&&this._$Eh.set(o,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const o=new Set(t.flat(1/0).reverse());for(const t of o)e.unshift(n(t))}else void 0!==t&&e.push(n(t));return e}static _$Eu(t,e){const o=e.attribute;return!1===o?void 0:"string"==typeof o?o:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const o of e.keys())this.hasOwnProperty(o)&&(t.set(o,this[o]),delete this[o]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((t,i)=>{if(o)t.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const o of i){const i=document.createElement("style"),s=e.litNonce;void 0!==s&&i.setAttribute("nonce",s),i.textContent=o.cssText,t.appendChild(i)}})(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,o){this._$AK(t,o)}_$ET(t,e){const o=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,o);if(void 0!==i&&!0===o.reflect){const s=(void 0!==o.converter?.toAttribute?o.converter:y).toAttribute(e,o.type);this._$Em=t,null==s?this.removeAttribute(i):this.setAttribute(i,s),this._$Em=null}}_$AK(t,e){const o=this.constructor,i=o._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=o.getPropertyOptions(i),s="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:y;this._$Em=i;const r=s.fromAttribute(e,t.type);this[i]=r??this._$Ej?.get(i)??r,this._$Em=null}}requestUpdate(t,e,o,i=!1,s){if(void 0!==t){const r=this.constructor;if(!1===i&&(s=this[t]),o??=r.getPropertyOptions(t),!((o.hasChanged??v)(s,e)||o.useDefault&&o.reflect&&s===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,o))))return;this.C(t,e,o)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:o,reflect:i,wrapped:s},r){o&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==s||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||o||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,o]of t){const{wrapped:t}=o,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,o,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[f("elementProperties")]=new Map,$[f("finalized")]=new Map,b?.({ReactiveElement:$}),(g.reactiveElementVersions??=[]).push("2.1.2");const A=globalThis,w=t=>t,S=A.trustedTypes,E=S?S.createPolicy("lit-html",{createHTML:t=>t}):void 0,k="$lit$",C=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+C,P=`<${T}>`,z=document,O=()=>z.createComment(""),M=t=>null===t||"object"!=typeof t&&"function"!=typeof t,U=Array.isArray,D="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,H=/>/g,j=RegExp(`>|${D}(?:([^\\s"'>=/]+)(${D}*=${D}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),F=/'/g,I=/"/g,B=/^(?:script|style|textarea|title)$/i,L=(t=>(e,...o)=>({_$litType$:t,strings:e,values:o}))(1),q=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),V=new WeakMap,K=z.createTreeWalker(z,129);function J(t,e){if(!U(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==E?E.createHTML(e):e}class Z{constructor({strings:t,_$litType$:e},o){let i;this.parts=[];let s=0,r=0;const a=t.length-1,n=this.parts,[l,c]=((t,e)=>{const o=t.length-1,i=[];let s,r=2===e?"<svg>":3===e?"<math>":"",a=N;for(let e=0;e<o;e++){const o=t[e];let n,l,c=-1,d=0;for(;d<o.length&&(a.lastIndex=d,l=a.exec(o),null!==l);)d=a.lastIndex,a===N?"!--"===l[1]?a=R:void 0!==l[1]?a=H:void 0!==l[2]?(B.test(l[2])&&(s=RegExp("</"+l[2],"g")),a=j):void 0!==l[3]&&(a=j):a===j?">"===l[0]?(a=s??N,c=-1):void 0===l[1]?c=-2:(c=a.lastIndex-l[2].length,n=l[1],a=void 0===l[3]?j:'"'===l[3]?I:F):a===I||a===F?a=j:a===R||a===H?a=N:(a=j,s=void 0);const h=a===j&&t[e+1].startsWith("/>")?" ":"";r+=a===N?o+P:c>=0?(i.push(n),o.slice(0,c)+k+o.slice(c)+C+h):o+C+(-2===c?e:h)}return[J(t,r+(t[o]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]})(t,e);if(this.el=Z.createElement(l,o),K.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=K.nextNode())&&n.length<a;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(k)){const e=c[r++],o=i.getAttribute(t).split(C),a=/([.?@])?(.*)/.exec(e);n.push({type:1,index:s,name:a[2],strings:o,ctor:"."===a[1]?tt:"?"===a[1]?et:"@"===a[1]?ot:Y}),i.removeAttribute(t)}else t.startsWith(C)&&(n.push({type:6,index:s}),i.removeAttribute(t));if(B.test(i.tagName)){const t=i.textContent.split(C),e=t.length-1;if(e>0){i.textContent=S?S.emptyScript:"";for(let o=0;o<e;o++)i.append(t[o],O()),K.nextNode(),n.push({type:2,index:++s});i.append(t[e],O())}}}else if(8===i.nodeType)if(i.data===T)n.push({type:2,index:s});else{let t=-1;for(;-1!==(t=i.data.indexOf(C,t+1));)n.push({type:7,index:s}),t+=C.length-1}s++}}static createElement(t,e){const o=z.createElement("template");return o.innerHTML=t,o}}function Q(t,e,o=t,i){if(e===q)return e;let s=void 0!==i?o._$Co?.[i]:o._$Cl;const r=M(e)?void 0:e._$litDirective$;return s?.constructor!==r&&(s?._$AO?.(!1),void 0===r?s=void 0:(s=new r(t),s._$AT(t,o,i)),void 0!==i?(o._$Co??=[])[i]=s:o._$Cl=s),void 0!==s&&(e=Q(t,s._$AS(t,e.values),s,i)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:o}=this._$AD,i=(t?.creationScope??z).importNode(e,!0);K.currentNode=i;let s=K.nextNode(),r=0,a=0,n=o[0];for(;void 0!==n;){if(r===n.index){let e;2===n.type?e=new G(s,s.nextSibling,this,t):1===n.type?e=new n.ctor(s,n.name,n.strings,this,t):6===n.type&&(e=new it(s,this,t)),this._$AV.push(e),n=o[++a]}r!==n?.index&&(s=K.nextNode(),r++)}return K.currentNode=z,i}p(t){let e=0;for(const o of this._$AV)void 0!==o&&(void 0!==o.strings?(o._$AI(t,o,e),e+=o.strings.length-2):o._$AI(t[e])),e++}}class G{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,o,i){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=o,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Q(this,t,e),M(t)?t===W||null==t||""===t?(this._$AH!==W&&this._$AR(),this._$AH=W):t!==this._$AH&&t!==q&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>U(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==W&&M(this._$AH)?this._$AA.nextSibling.data=t:this.T(z.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:o}=t,i="number"==typeof o?this._$AC(t):(void 0===o.el&&(o.el=Z.createElement(J(o.h,o.h[0]),this.options)),o);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new X(i,this),o=t.u(this.options);t.p(e),this.T(o),this._$AH=t}}_$AC(t){let e=V.get(t.strings);return void 0===e&&V.set(t.strings,e=new Z(t)),e}k(t){U(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let o,i=0;for(const s of t)i===e.length?e.push(o=new G(this.O(O()),this.O(O()),this,this.options)):o=e[i],o._$AI(s),i++;i<e.length&&(this._$AR(o&&o._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=w(t).nextSibling;w(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class Y{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,o,i,s){this.type=1,this._$AH=W,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=s,o.length>2||""!==o[0]||""!==o[1]?(this._$AH=Array(o.length-1).fill(new String),this.strings=o):this._$AH=W}_$AI(t,e=this,o,i){const s=this.strings;let r=!1;if(void 0===s)t=Q(this,t,e,0),r=!M(t)||t!==this._$AH&&t!==q,r&&(this._$AH=t);else{const i=t;let a,n;for(t=s[0],a=0;a<s.length-1;a++)n=Q(this,i[o+a],e,a),n===q&&(n=this._$AH[a]),r||=!M(n)||n!==this._$AH[a],n===W?t=W:t!==W&&(t+=(n??"")+s[a+1]),this._$AH[a]=n}r&&!i&&this.j(t)}j(t){t===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class tt extends Y{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===W?void 0:t}}class et extends Y{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==W)}}class ot extends Y{constructor(t,e,o,i,s){super(t,e,o,i,s),this.type=5}_$AI(t,e=this){if((t=Q(this,t,e,0)??W)===q)return;const o=this._$AH,i=t===W&&o!==W||t.capture!==o.capture||t.once!==o.once||t.passive!==o.passive,s=t!==W&&(o===W||i);i&&this.element.removeEventListener(this.name,this,o),s&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class it{constructor(t,e,o){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=o}get _$AU(){return this._$AM._$AU}_$AI(t){Q(this,t)}}const st={I:G},rt=A.litHtmlPolyfillSupport;rt?.(Z,G),(A.litHtmlVersions??=[]).push("3.3.2");const at=globalThis;let nt=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,o)=>{const i=o?.renderBefore??e;let s=i._$litPart$;if(void 0===s){const t=o?.renderBefore??null;i._$litPart$=s=new G(e.insertBefore(O(),t),t,void 0,o??{})}return s._$AI(t),s})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}};nt._$litElement$=!0,nt.finalized=!0,at.litElementHydrateSupport?.({LitElement:nt});const lt=at.litElementPolyfillSupport;lt?.({LitElement:nt}),(at.litElementVersions??=[]).push("4.2.2");const ct=t=>(e,o)=>{void 0!==o?o.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)},dt={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:v},ht=(t=dt,e,o)=>{const{kind:i,metadata:s}=o;let r=globalThis.litPropertyMetadata.get(s);if(void 0===r&&globalThis.litPropertyMetadata.set(s,r=new Map),"setter"===i&&((t=Object.create(t)).wrapped=!0),r.set(o.name,t),"accessor"===i){const{name:i}=o;return{set(o){const s=e.get.call(this);e.set.call(this,o),this.requestUpdate(i,s,t,!0,o)},init(e){return void 0!==e&&this.C(i,void 0,t,e),e}}}if("setter"===i){const{name:i}=o;return function(o){const s=this[i];e.call(this,o),this.requestUpdate(i,s,t,!0,o)}}throw Error("Unsupported decorator location: "+i)};function pt(t){return(e,o)=>"object"==typeof o?ht(t,e,o):((t,e,o)=>{const i=e.hasOwnProperty(o);return e.constructor.createProperty(o,t),i?Object.getOwnPropertyDescriptor(e,o):void 0})(t,e,o)}function ut(t){return pt({...t,state:!0,attribute:!1})}async function gt(t){return(await t.callWS({type:"abode_security/actions/list"})).actions}async function mt(t){return(await t.callWS({type:"abode_security/modes/list"})).modes}async function _t(t){return(await t.callWS({type:"abode_security/entities/sensors"})).sensors}async function bt(t){return(await t.callWS({type:"abode_security/entities/alarms"})).alarms}async function ft(t,e,o){return t.callWS({type:"abode_security/actions/update",action_id:e,...o})}let yt=class extends nt{constructor(){super(...arguments),this._modes=[],this._actions=[],this._loading=!0,this._error=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}async _loadData(){this._loading=!0,this._error=null;try{const[t,e]=await Promise.all([mt(this.hass),gt(this.hass)]);this._modes=t??[],this._actions=e??[]}catch(t){this._error=t instanceof Error?t.message:"Failed to load data"}finally{this._loading=!1}}_getActionsForMode(t){return this._actions.filter(e=>e.enabled&&e.modes.includes(t))}render(){return this._loading?L`<div class="loading">Loading modes...</div>`:this._error?L`<div class="error" role="alert">${this._error}</div>`:L`
      <div class="modes-grid">
        ${this._modes.map(t=>this._renderModeCard(t))}
      </div>
    `}_renderModeCard(t){const e=this._getActionsForMode(t.id);return L`
      <div class="mode-card ${t.active?"active":""}">
        <div class="mode-header">
          <div class="mode-icon">
            <ha-icon icon=${t.icon}></ha-icon>
          </div>
          <div class="mode-info">
            <h3>${t.name}</h3>
            <div class="badges">
              <span class="badge">${t.action_count} actions</span>
              ${t.active?L`<span class="badge active">Active</span>`:""}
            </div>
          </div>
        </div>

        ${e.length>0?L`
              <ul class="action-list" aria-label="Actions for ${t.name} mode">
                ${e.map(t=>L`
                    <li>
                      <ha-icon icon="mdi:bell-ring"></ha-icon>
                      ${t.name}
                    </li>
                  `)}
              </ul>
            `:L`<div class="empty-actions">No actions configured</div>`}
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
  `,t([pt({attribute:!1})],yt.prototype,"hass",void 0),t([ut()],yt.prototype,"_modes",void 0),t([ut()],yt.prototype,"_actions",void 0),t([ut()],yt.prototype,"_loading",void 0),t([ut()],yt.prototype,"_error",void 0),yt=t([ct("abode-modes-tab")],yt);const vt=2;let xt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,o){this._$Ct=t,this._$AM=e,this._$Ci=o}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};const{I:$t}=st,At=t=>t,wt=()=>document.createComment(""),St=(t,e,o)=>{const i=t._$AA.parentNode,s=void 0===e?t._$AB:e._$AA;if(void 0===o){const e=i.insertBefore(wt(),s),r=i.insertBefore(wt(),s);o=new $t(e,r,t,t.options)}else{const e=o._$AB.nextSibling,r=o._$AM,a=r!==t;if(a){let e;o._$AQ?.(t),o._$AM=t,void 0!==o._$AP&&(e=t._$AU)!==r._$AU&&o._$AP(e)}if(e!==s||a){let t=o._$AA;for(;t!==e;){const e=At(t).nextSibling;At(i).insertBefore(t,s),t=e}}}return o},Et=(t,e,o=t)=>(t._$AI(e,o),t),kt={},Ct=(t,e=kt)=>t._$AH=e,Tt=t=>{t._$AR(),t._$AA.remove()},Pt=(t,e,o)=>{const i=new Map;for(let s=e;s<=o;s++)i.set(t[s],s);return i},zt=(t=>(...e)=>({_$litDirective$:t,values:e}))(class extends xt{constructor(t){if(super(t),t.type!==vt)throw Error("repeat() can only be used in text expressions")}dt(t,e,o){let i;void 0===o?o=e:void 0!==e&&(i=e);const s=[],r=[];let a=0;for(const e of t)s[a]=i?i(e,a):a,r[a]=o(e,a),a++;return{values:r,keys:s}}render(t,e,o){return this.dt(t,e,o).values}update(t,[e,o,i]){const s=(t=>t._$AH)(t),{values:r,keys:a}=this.dt(e,o,i);if(!Array.isArray(s))return this.ut=a,r;const n=this.ut??=[],l=[];let c,d,h=0,p=s.length-1,u=0,g=r.length-1;for(;h<=p&&u<=g;)if(null===s[h])h++;else if(null===s[p])p--;else if(n[h]===a[u])l[u]=Et(s[h],r[u]),h++,u++;else if(n[p]===a[g])l[g]=Et(s[p],r[g]),p--,g--;else if(n[h]===a[g])l[g]=Et(s[h],r[g]),St(t,l[g+1],s[h]),h++,g--;else if(n[p]===a[u])l[u]=Et(s[p],r[u]),St(t,s[h],s[p]),p--,u++;else if(void 0===c&&(c=Pt(a,u,g),d=Pt(n,h,p)),c.has(n[h]))if(c.has(n[p])){const e=d.get(a[u]),o=void 0!==e?s[e]:null;if(null===o){const e=St(t,s[h]);Et(e,r[u]),l[u]=e}else l[u]=Et(o,r[u]),St(t,s[h],o),s[e]=null;u++}else Tt(s[p]),p--;else Tt(s[h]),h++;for(;u<=g;){const e=St(t,l[g+1]);Et(e,r[u]),l[u++]=e}for(;h<=p;){const t=s[h++];null!==t&&Tt(t)}return this.ut=a,Ct(t,l),q}});let Ot=0,Mt=class extends nt{constructor(){super(...arguments),this.heading="",this.variant="dialog",this.size="sm",this.dismissOnOverlay=!0,this.dismissOnEscape=!0,this._hasFooterContent=!1,this._headingId="abode-modal-heading-"+ ++Ot,this._onOverlayClick=t=>{this.dismissOnOverlay&&t.target===t.currentTarget&&this._dismiss()},this._onKeydown=t=>{this.dismissOnEscape&&"Escape"===t.key&&this._dismiss()},this._onFooterSlotChange=t=>{const e=t.target;this._hasFooterContent=e.assignedElements().length>0}}_dismiss(){this.dispatchEvent(new CustomEvent("dismiss",{bubbles:!0,composed:!0}))}render(){return L`
      <div
        class="modal-overlay"
        @click=${this._onOverlayClick}
        @keydown=${this._onKeydown}
      >
        <div
          class="modal-box"
          role=${this.variant}
          aria-modal="true"
          aria-labelledby=${this._headingId}
          data-size=${this.size}
        >
          <h2 id=${this._headingId}>${this.heading}</h2>
          <slot></slot>
          <div class="modal-footer" ?hidden=${!this._hasFooterContent}>
            <slot name="footer" @slotchange=${this._onFooterSlotChange}></slot>
          </div>
        </div>
      </div>
    `}};Mt.styles=a`
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
  `,t([pt({type:String})],Mt.prototype,"heading",void 0),t([pt({type:String})],Mt.prototype,"variant",void 0),t([pt({type:String})],Mt.prototype,"size",void 0),t([pt({type:Boolean,attribute:"dismiss-on-overlay"})],Mt.prototype,"dismissOnOverlay",void 0),t([pt({type:Boolean,attribute:"dismiss-on-escape"})],Mt.prototype,"dismissOnEscape",void 0),t([ut()],Mt.prototype,"_hasFooterContent",void 0),Mt=t([ct("abode-modal")],Mt);let Ut=class extends nt{constructor(){super(...arguments),this.action=null,this._name="",this._modes=[],this._delaySeconds=0,this._selectedSensors=[],this._selectedAlarms=[],this._sensors=null,this._alarms=[],this._errors={},this._saving=!1,this._loading=!0}async connectedCallback(){super.connectedCallback(),await this._loadEntities(),this.action&&this._populateForm()}async _loadEntities(){this._loading=!0;try{const[t,e]=await Promise.all([_t(this.hass),bt(this.hass)]);this._sensors=t??null,this._alarms=e??[]}catch(t){console.error("Failed to load entities:",t)}finally{this._loading=!1}}_populateForm(){this.action&&(this._name=this.action.name,this._modes=[...this.action.modes],this._delaySeconds=this.action.delay_seconds,this._selectedSensors=[...this.action.sensor_entity_ids],this._selectedAlarms=[...this.action.alarm_entity_ids])}_toggleMode(t){this._modes.includes(t)?this._modes=this._modes.filter(e=>e!==t):this._modes=[...this._modes,t],this._clearError("modes")}_toggleSensor(t){this._selectedSensors.includes(t)?this._selectedSensors=this._selectedSensors.filter(e=>e!==t):this._selectedSensors=[...this._selectedSensors,t],this._clearError("sensors")}_toggleAlarm(t){this._selectedAlarms.includes(t)?this._selectedAlarms=this._selectedAlarms.filter(e=>e!==t):this._selectedAlarms=[...this._selectedAlarms,t],this._clearError("alarms")}_isCategorySelected(t){if(!this._sensors)return!1;const e=this._sensors[t]||[];return 0!==e.length&&e.every(t=>this._selectedSensors.includes(t.entity_id))}_isCategoryPartial(t){if(!this._sensors)return!1;const e=this._sensors[t]||[];if(0===e.length)return!1;const o=e.filter(t=>this._selectedSensors.includes(t.entity_id));return o.length>0&&o.length<e.length}_toggleCategory(t){if(!this._sensors)return;const e=(this._sensors[t]||[]).map(t=>t.entity_id);if(this._isCategorySelected(t))this._selectedSensors=this._selectedSensors.filter(t=>!e.includes(t));else{const t=e.filter(t=>!this._selectedSensors.includes(t));this._selectedSensors=[...this._selectedSensors,...t]}this._clearError("sensors")}_clearError(t){if(this._errors[t]){const{[t]:e,...o}=this._errors;this._errors=o}}_validate(){return this._errors={},this._name.trim()||(this._errors={...this._errors,name:"Name is required"}),0===this._modes.length&&(this._errors={...this._errors,modes:"Select at least one mode"}),0===this._selectedSensors.length&&(this._errors={...this._errors,sensors:"Select at least one sensor"}),0===this._selectedAlarms.length&&(this._errors={...this._errors,alarms:"Select at least one alarm"}),0===Object.keys(this._errors).length}async _handleSave(){if(this._validate()){this._saving=!0;try{const t={name:this._name.trim(),modes:this._modes,delay_seconds:this._delaySeconds,sensor_entity_ids:this._selectedSensors,alarm_entity_ids:this._selectedAlarms};this.action?await ft(this.hass,this.action.id,t):await async function(t,e){return t.callWS({type:"abode_security/actions/create",...e})}(this.hass,t),this.dispatchEvent(new CustomEvent("save"))}catch(t){console.error("Failed to save action:",t),this._errors={...this._errors,form:t instanceof Error?t.message:"Failed to save"}}finally{this._saving=!1}}}_handleCancel(){this.dispatchEvent(new CustomEvent("cancel"))}render(){return L`
      <abode-modal
        heading=${this.action?"Edit Action":"New Action"}
        size="lg"
        @dismiss=${this._handleCancel}
      >
        ${this._loading?L`<div class="loading">Loading...</div>`:this._renderFormBody()}
        ${this._loading?"":this._renderFooter()}
      </abode-modal>
    `}_renderFormBody(){return L`
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
        ${this._errors.name?L`<span class="error-text">${this._errors.name}</span>`:""}
      </div>

      <div class="form-group">
        <label>Modes (at least one required)</label>
        <div class="checkbox-group">
          ${["standby","home","away"].map(t=>L`
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
        ${this._errors.modes?L`<span class="error-text">${this._errors.modes}</span>`:""}
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
        ${this._errors.sensors?L`<span class="error-text">${this._errors.sensors}</span>`:""}
      </div>

      <div class="form-group">
        <label>Alarms to trigger (at least one required)</label>
        ${this._renderAlarmSelection()}
        ${this._errors.alarms?L`<span class="error-text">${this._errors.alarms}</span>`:""}
      </div>

      ${this._errors.form?L`<div class="error-text" style="margin-bottom: 16px;">
            ${this._errors.form}
          </div>`:""}
    `}_renderFooter(){return L`
      <button slot="footer" class="cancel" @click=${this._handleCancel}>
        Cancel
      </button>
      <button
        slot="footer"
        class="primary"
        @click=${this._handleSave}
        ?disabled=${this._saving}
      >
        ${this._saving?"Saving...":"Save"}
      </button>
    `}_renderSensorSelection(){const t=this._sensors;if(!t)return L`<div class="loading">Loading sensors...</div>`;const e=Object.keys(t).filter(e=>(t[e]??[]).length>0).sort();return 0===e.length?L`<div class="loading">No sensors available</div>`:L`
      <div class="sensor-categories">
        ${e.map(e=>{const o=t[e]??[];return L`
            <div class="category">
              <div class="category-header" @click=${()=>this._toggleCategory(e)}>
                <input
                  type="checkbox"
                  .checked=${this._isCategorySelected(e)}
                  .indeterminate=${this._isCategoryPartial(e)}
                  @click=${t=>t.stopPropagation()}
                  @change=${()=>this._toggleCategory(e)}
                />
                <span>${e.replace(/_/g," ")} (${o.length})</span>
              </div>
              <div class="category-items">
                ${o.map(t=>L`
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
    `}_renderAlarmSelection(){return 0===this._alarms.length?L`<div class="loading">No alarms available</div>`:L`
      <div class="alarm-list">
        ${this._alarms.map(t=>L`
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
    `}};Ut.styles=a`
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
  `,t([pt({attribute:!1})],Ut.prototype,"hass",void 0),t([pt({attribute:!1})],Ut.prototype,"action",void 0),t([ut()],Ut.prototype,"_name",void 0),t([ut()],Ut.prototype,"_modes",void 0),t([ut()],Ut.prototype,"_delaySeconds",void 0),t([ut()],Ut.prototype,"_selectedSensors",void 0),t([ut()],Ut.prototype,"_selectedAlarms",void 0),t([ut()],Ut.prototype,"_sensors",void 0),t([ut()],Ut.prototype,"_alarms",void 0),t([ut()],Ut.prototype,"_errors",void 0),t([ut()],Ut.prototype,"_saving",void 0),t([ut()],Ut.prototype,"_loading",void 0),Ut=t([ct("abode-action-editor")],Ut);let Dt=class extends nt{constructor(){super(...arguments),this._actions=[],this._loading=!0,this._error=null,this._editingAction=null,this._showEditor=!1,this._confirm=null,this._togglingIds=new Set,this._operationError=null}async connectedCallback(){super.connectedCallback(),await this._loadData()}async _loadData(){this._loading=!0,this._error=null;try{this._actions=await gt(this.hass)??[]}catch(t){this._error=t instanceof Error?t.message:"Failed to load actions"}finally{this._loading=!1}}_getRecentTriggers(){return(this._actions??[]).filter(t=>t.last_triggered).sort((t,e)=>new Date(e.last_triggered).getTime()-new Date(t.last_triggered).getTime()).slice(0,5)}_formatTime(t){if(!t)return"";const e=new Date(t),o=(new Date).getTime()-e.getTime(),i=Math.floor(o/6e4),s=Math.floor(o/36e5),r=Math.floor(o/864e5);return i<1?"Just now":i<60?`${i}m ago`:s<24?`${s}h ago`:r<7?`${r}d ago`:e.toLocaleDateString()}_addAction(){this._editingAction=null,this._showEditor=!0}_editAction(t){this._editingAction=t,this._showEditor=!0}async _toggleAction(t){const e=t.id;this._togglingIds=new Set([...this._togglingIds,e]),this._operationError=null;try{const o=await ft(this.hass,e,{enabled:!t.enabled});this._actions=this._actions.map(t=>t.id===e?o:t)}catch(e){console.error("Failed to toggle action:",e),this._operationError=`Failed to ${t.enabled?"disable":"enable"} action`}finally{this._togglingIds=new Set([...this._togglingIds].filter(t=>t!==e))}}_requestDelete(t){this._confirm={kind:"delete",action:t}}async _confirmDelete(){if("delete"!==this._confirm?.kind)return;const{action:t}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/delete",action_id:e})}(this.hass,t.id),this._actions=this._actions.filter(e=>e.id!==t.id)}catch(t){console.error("Failed to delete action:",t),this._operationError="Failed to delete action"}}_requestTest(t){this._confirm={kind:"test",action:t}}async _confirmTest(){if("test"!==this._confirm?.kind)return;const{action:t}=this._confirm;this._confirm=null,this._operationError=null;try{await async function(t,e){await t.callWS({type:"abode_security/actions/test",action_id:e})}(this.hass,t.id)}catch(t){console.error("Failed to test action:",t),this._operationError="Failed to test action"}}_closeEditor(){this._showEditor=!1,this._editingAction=null}async _handleSave(){this._closeEditor(),await this._loadData()}render(){if(this._loading)return L`<div class="loading">Loading actions...</div>`;if(this._error)return L`<div class="error" role="alert">${this._error}</div>`;const t=this._getRecentTriggers();return L`
      ${this._operationError?L`
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

      ${0===this._actions.length?L`
            <div class="empty-state">
              <ha-icon icon="mdi:bell-off-outline"></ha-icon>
              <p>No actions configured</p>
              <button class="add-button" @click=${this._addAction}>
                <ha-icon icon="mdi:plus"></ha-icon>
                Create your first action
              </button>
            </div>
          `:L`
            <div class="actions-list" role="list">
              ${zt(this._actions,t=>t.id,t=>this._renderActionRow(t))}
            </div>
          `}

      <div class="recent-triggers">
        <h3>Recent Triggers</h3>
        ${0===t.length?L`<div class="empty-state" style="padding: 24px;">
              No recent triggers
            </div>`:L`
              <div class="trigger-list">
                ${t.map(t=>L`
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

      ${this._showEditor?L`
            <abode-action-editor
              .hass=${this.hass}
              .action=${this._editingAction}
              @save=${this._handleSave}
              @cancel=${this._closeEditor}
            ></abode-action-editor>
          `:""}
      ${"delete"===this._confirm?.kind?this._renderDeleteDialog():""}
      ${"test"===this._confirm?.kind?this._renderTestDialog():""}
    `}_renderActionRow(t){const e=this._togglingIds.has(t.id);return L`
      <div class="action-row ${t.enabled?"":"disabled"}" role="listitem">
        <div class="action-info">
          <div class="action-name">${t.name}</div>
          <div class="action-meta">
            <div class="modes-list">
              ${t.modes.map(t=>L`<span class="mode-chip">${t}</span>`)}
            </div>
            ${t.trigger_count>0?L`<span class="trigger-info"
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
    `}_renderDeleteDialog(){return L`
      <abode-modal
        heading="Delete Action"
        variant="alertdialog"
        @dismiss=${()=>this._confirm=null}
      >
        <p>
          Delete action "${this._confirm?.action.name}"? This cannot be undone.
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${()=>this._confirm=null}
        >
          Cancel
        </button>
        <button
          slot="footer"
          class="dialog-button danger"
          @click=${this._confirmDelete}
        >
          Delete
        </button>
      </abode-modal>
    `}_renderTestDialog(){return L`
      <abode-modal
        heading="Test Action"
        variant="alertdialog"
        @dismiss=${()=>this._confirm=null}
      >
        <p>
          This will trigger real alarms. Are you sure you want to test
          "${this._confirm?.action.name}"?
        </p>
        <button
          slot="footer"
          class="dialog-button cancel"
          @click=${()=>this._confirm=null}
        >
          Cancel
        </button>
        <button
          slot="footer"
          class="dialog-button primary"
          @click=${this._confirmTest}
        >
          Test
        </button>
      </abode-modal>
    `}};Dt.styles=a`
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
  `,t([pt({attribute:!1})],Dt.prototype,"hass",void 0),t([ut()],Dt.prototype,"_actions",void 0),t([ut()],Dt.prototype,"_loading",void 0),t([ut()],Dt.prototype,"_error",void 0),t([ut()],Dt.prototype,"_editingAction",void 0),t([ut()],Dt.prototype,"_showEditor",void 0),t([ut()],Dt.prototype,"_confirm",void 0),t([ut()],Dt.prototype,"_togglingIds",void 0),t([ut()],Dt.prototype,"_operationError",void 0),Dt=t([ct("abode-actions-tab")],Dt);let Nt=class extends nt{constructor(){super(...arguments),this._activeTab="actions"}render(){const t="modes"===this._activeTab?"modes-panel":"actions-panel";return L`
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
          id=${t}
          aria-labelledby=${"modes"===this._activeTab?"modes-tab":"actions-tab"}
        >
          ${"modes"===this._activeTab?L`<abode-modes-tab .hass=${this.hass}></abode-modes-tab>`:L`<abode-actions-tab .hass=${this.hass}></abode-actions-tab>`}
        </div>
      </div>
    `}};Nt.styles=a`
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
  `,t([pt({attribute:!1})],Nt.prototype,"hass",void 0),t([ut()],Nt.prototype,"_activeTab",void 0),Nt=t([ct("abode-configuration-panel")],Nt);export{Nt as AbodeConfigurationPanel};
